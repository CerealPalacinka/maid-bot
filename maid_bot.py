import os
import discord
import atexit
import time
import json
import asyncio
import random
import linkdatabase

from discord.ext import commands
from datetime import datetime
from copy import deepcopy
from dotenv import load_dotenv


load_dotenv()
bot = commands.Bot(command_prefix=os.getenv('DISCORD_PREFIX'))

FP_DATA = 'data.json'
FP_RESPONSES = 'responses.json'

RESPONSES = dict()
TEMP_MASTER = dict(id=0, reminders=[], index=0, asking=False, wait=False, snooze=600, message=0)
TEMP_REMINDER = dict(time=0, name='')

LATE_THRESHOLD_TIME = 300

date = None

update_task = None
reminders = []

masters = []


@bot.event
async def on_ready():

	# load all masters and their reminders from json
	data_load()
	await bot.change_presence(activity=discord.Game("with copy.deepcopy()"))
	

	for master in masters:
		if master['asking'] and master['message'] != 0:
			message = await get_master_message(master)

			await message.remove_reaction("✅", bot.user)
			await message.remove_reaction("⏰", bot.user)

			await message.add_reaction("✅")

		if master['wait'] and not master['id'] in reminders:
			reminder_start(master, True, True)


	update_restart()
	print("maid bot is ready.\n")


@bot.event
async def on_raw_reaction_add(payload):
	dm = bot.get_channel(payload.channel_id)
	message = await dm.fetch_message(payload.message_id)

	for reaction in message.reactions:
		if reaction.count > 1:

			# remove reactions
			await reaction.message.remove_reaction("✅", bot.user)
			await reaction.message.remove_reaction("⏰", bot.user)

			master = None
			async for user in reaction.users():
				if user is not bot.user:
					master = get_master(user.id)
					break
			
			if reaction.emoji == "✅":  # iterate index
				master['index'] += 1
				master['asking'] = False

				reminder_cancel(master["id"])

				if master['index'] == len(master['reminders']) and master['wait']:
					master['wait'] = False
					master['index'] = 0

				data_save()
				update_restart()
				await send_congrats(master)
			elif reaction.emoji == "⏰":  # ask again after snooze
				await send_snooze(master)
			
			break


async def update():
	while not bot.is_closed():

		global date
		if date.day != datetime.now().day:
			date = datetime.now()
			for master in masters:
				if master['index'] == len(master['reminders']):
					master['index'] = 0
				else:
					master['wait'] = True
			print("new day")
			data_save()

		t = get_seconds()
		delta = 86400 - t  # time till midnight

		alarms = []
		# find smallest delta
		for master in masters:
			if not master['wait'] and master["index"] < len(master["reminders"]) and not master["asking"]:
				master_delta = master["reminders"][master["index"]]["time"] - t

				print(f"id:{master['id']}, master_delta: {master_delta}, delta:{delta}")
				if master_delta > 0:
					if master_delta < delta:
						delta = master_delta
				else:
					# if delta is below zero add master to alert list
					alarms.append([master, master_delta])

		# alert all masters
		for alarm in alarms:
			# is bot late to alert master
			master = alarm[0]
			late = abs(alarm[1]) > LATE_THRESHOLD_TIME

			print(f"alarm id:{master['id']} late: {late}")

			master["asking"] = True

			reminder_start(master, late)

		data_save()

		# continue loop after delta seconds
		print(f"sleep for {delta}")
		await asyncio.sleep(delta)


def update_restart():  # restart update loop
	global update_task
	if update_task is not None:
		update_task.cancel()
	update_task = bot.loop.create_task(update())


@bot.command(help='i wont forgive you if u use this')
async def bully(ctx):
	users = []
	for i in masters:
		if ctx.message.author.id != i["id"]:
			users.append(f'<@{i["id"]}>')
			print(users)
	await ctx.send(f'nyaa!! {random.choice(users)} 😿 help me pls!!!')


@bot.command(name='img')
async def img(ctx):
	await ctx.message.delete()
	embed = discord.Embed()
	embed.set_image(url = random.choice(linkdatabase.armpitst))
	await ctx.send(embed=embed)
	pass


@bot.command(help='adds a reminder to your list \nfor best result use imperative mood', usage='08:00 make coffee')
async def add(ctx, _time:str, *_name:str):
	# users id
	id = ctx.message.author.id

	master = get_master(id)

	# if user isn't a master, create a new master from a template and assign users id
	if master is None:
		master = deepcopy(TEMP_MASTER)
		master["id"] = id
		masters.append(master)
		print(f"created new master with id {id}")

	# add a new activity and save
	reminder_add(master, ctx, _time, _name)
	data_save()

	update_restart()

	await send_add(ctx)


@bot.command(name='list', help='shows your list of reminders')
async def _list(ctx):

	master = get_master(ctx.message.author.id)
	if master is not None and len(master["reminders"]) > 0:
		items = []

		# append all masters reminders
		for i in range(0, len(master["reminders"])):

			item = RESPONSES['list_item']
			if i == master['index']:
				item = RESPONSES['list_current']
			
			activity = master["reminders"][i]

			items.append(item.format(
				i,
				seconds_to_time(activity["time"]),
				activity["name"]))

		# format into code block
		block = RESPONSES['list_block'].format(
			ctx.message.author.display_name,
			'\n'.join(items))

		await delete_user_message(ctx)

		await send_list(ctx, block)
	else: 
		await send_list_no(ctx)


@bot.command(help='removes element from your list by index')
async def remove(ctx, index:int):
	master = get_master(ctx.message.author.id)
	length = len(master["reminders"])

	# check if list is not empty
	if master is not None and length > 0:

		# check index validity
		if 0 <= index < length:

			# set back index if removed activity already happend
			if master["index"] > index and master["index"] != 0:
				master["index"] -= 1

			master["reminders"].pop(index)
			data_save()

			update_restart()

			await send_remove(ctx)
		else:
			await ctx.send('no')
	else:
		await send_list_no(ctx)


@bot.command(help='clears your list')
async def removeall(ctx):
	master = get_master(ctx.message.author.id)

	# check if list is not empty
	if master is not None and len(master["reminders"]) > 0:
		master["reminders"].clear()
		data_save()

		update_restart()

		await send_remove(ctx, True)
	else:
		await send_list_no(ctx)


@bot.command(name='get', help='gets value property from your config', usage='snooze')
async def get(ctx, key:str):
	master = get_master(ctx.message.author.id)

	await delete_user_message(ctx)

	if master is not None and key in master:
		await ctx.send(f"```fix\n'{key}': {master[key]}```")
	else:
		await ctx.send('no')


@bot.command(name='set', help='sets value property for your config', usage='snooze 600')
async def _set(ctx, key:str, value):
	master = get_master(ctx.message.author.id)
	value_new = eval(value)

	await delete_user_message(ctx)

	if master is not None and key in master and type(master[key]) == type(value_new):
		old = master[key]
		master[key] = value_new
		data_save()

		# format into code block
		block = RESPONSES['set_block'].format(
			ctx.message.author.display_name,
			key,
			old,
			value)

		await send_set(ctx, block)
	else:
		await ctx.send('no')


@bot.command()
async def stop(ctx):
	if ctx.message.author.id == 204981328305848330 or ctx.message.author.id == 270603696683876352:
		bot.loop.stop()
	else:
		await ctx.send("nice try smartest")


@atexit.register
async def exit_handler():
	print("stopping maid bot.")


async def delete_user_message(ctx):
	if ctx.guild is not None:
		await ctx.message.delete()


def reminder_cancel(master_id):
	for reminder in reminders:
		if reminder[0] == master_id:
			reminder[1].cancel()
			reminders.remove(reminder)
			break


def reminder_start(master, late=False, delay=False):
	task = bot.loop.create_task(send_ask(master, late, delay))
	id = master["id"]
	new_reminder = [id, task]
	reminders.append(new_reminder)


async def send_ask(master, late=False, delay=False):
	print(f'active reminders:\n{reminders}')

	if delay:
		await asyncio.sleep(master['snooze'])

	sorry = ""
	if late:
		sorry = response('late') + " "
	activity = master["reminders"][master["index"]]["name"]

	message = await bot.get_user(master["id"]).send(response('ask').format(response('hello'), sorry, activity))
	
	master['message'] = message.id
	data_save()
	
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

	await asyncio.sleep(master['snooze'])
	await message.delete()
	await send_ask(master)


async def send_congrats(master):
	await bot.get_user(master["id"]).send(response('congrats').format(response('emoji')))


async def send_snooze(master):
	snooze_time = master['snooze']
	t = f"{int(snooze_time / 60)} minutes"
	await bot.get_user(master["id"]).send(response('snooze').format(t))

	reminder_cancel(master["id"])
	await asyncio.sleep(snooze_time)

	reminder_start(master)


async def send_add(ctx):
	await ctx.send(response('add').format(
		response('hello'),
		response('activity'),
		response('tasks'),
		response('end')))


async def send_list(ctx, block):
	await ctx.send(response('list').format(
		response('hello'),
		response('tasks'),
		response('end'),
		block))


async def send_list_no(ctx):
	await ctx.send(response('list_no').format(
		response('hello'),
		response('tasks')))


async def send_remove(ctx, all=False):
	activity = response('activity')
	if all:
		activity = 'everything'

	await ctx.send(response('remove').format(
		response('hello'),
		activity,
		response('tasks')))


async def send_set(ctx, block):
	await ctx.send(response('set').format(
		response('hello'),
		block))


def response(key):
	return random.choice(RESPONSES[key])


def get_master(id):
	for master in masters:
		if master["id"] == id:
			return master
	return None


async def get_master_message(master):
	if master['message'] == 0:
		return None
	
	user = bot.get_user(master['id'])
	return await user.fetch_message(master['message'])


def reminder_add(master, ctx, _time, _name):

	# create a new activity from a template
	new_activity = deepcopy(TEMP_REMINDER)

	t = max(0, min(time_to_seconds(_time), 86340))
	ask = t > get_seconds()

	new_activity["time"] = t
	new_activity["name"] = " ".join(_name)

	index = None
	for i in range(0, len(master["reminders"])):
		if master["reminders"][i]["time"] > new_activity["time"]:
			index = i
			break

	# add activity to the master reminders array
	if index is not None:
		if master["index"] > index or master["index"] == index and not ask:
			master["index"] += 1
		master["reminders"].insert(i, new_activity)
	else:
		if master["index"] == len(master["reminders"]) and not ask:
			master["index"] += 1
		master["reminders"].append(new_activity)
	print (f"added new activity for master {master['id']} {new_activity}")


def time_to_seconds(time_string):
	h, m = time_string.split(":")
	return int(h) * 3600 + int(m) * 60


def seconds_to_time(seconds):
	return time.strftime("%H:%M", time.gmtime(seconds))


def get_seconds():
	return datetime.now().hour * 3600 + datetime.now().minute * 60 + datetime.now().second


def data_save():
	out = [date.year, date.month, date.day]
	save_data = dict(date=out, masters=masters)

	with open(FP_DATA, 'w') as fp:
		json.dump(save_data, fp, indent="\t")
		print("saved data to json")


def data_load():

	# load date and masters
	with open(FP_DATA) as fp:
		jsondata = json.load(fp)

		global date
		date_list = jsondata["date"]
		y, m, d = date_list[0], date_list[1], date_list[2]
		date = datetime(y, m, d)

		global masters
		masters = jsondata["masters"]

	# load Responses
	with open(FP_RESPONSES) as fp:
		global RESPONSES
		RESPONSES = json.load(fp)

	print("loaded data from json")

bot.run(os.getenv('DISCORD_TOKEN'))
