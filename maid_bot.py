import os
import discord
import atexit
import time
import json
import asyncio
import random
import linkdatabase

from discord.ext import commands
from discord.ext.commands import Context
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

lurk_counter = [0, 0]


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
	
	if not reminders:
		for master in masters:
			if master['wait'] and not master['id'] in reminders:
				reminder_start(master, False, True)

	update_restart()
	print("maid bot is ready.\n")


@bot.event
async def on_raw_reaction_add(payload:discord.RawReactionActionEvent):
	dm = bot.get_channel(payload.channel_id)
	message = await dm.fetch_message(payload.message_id)

	for reaction in message.reactions:
		if reaction.me and reaction.count > 1:

			# remove reactions
			await reaction.message.remove_reaction("✅", bot.user)
			await reaction.message.remove_reaction("⏰", bot.user)

			master = None
			async for user in reaction.users():
				if user is not bot.user:
					master = get_master(user.id)
					break
			
			if reaction.emoji == "✅":  # iterate index
				await reminder_next(master)
			elif reaction.emoji == "⏰":  # ask again after snooze
				await snooze(master)
			
			break


@bot.event
async def on_message(message:discord.Message):
	prefixes = ('+', '*', '!', '+')
	for prefix in prefixes:
		if message.content.startswith(prefix):
			bot.loop.create_task(delete_user_message(message))
			return

	master = get_master(message.author.id)
	if master is not None:
		bot.loop.create_task(lurk(message))
		
	await bot.process_commands(message)


@bot.command()
async def test(ctx:Context, user_id:int, message_id:int):
	user = bot.get_user(user_id)
	msg = await user.fetch_message(message_id)
	print (f'user:{user} msg:{msg}')


async def lurk(message:discord.Message):
	
	# wait for embeds to load
	await asyncio.sleep(1)
	if message.embeds or message.attachments:

		old_id = lurk_counter[1]
		lurk_counter[1] = message.author.id

		# same author
		if lurk_counter[1] == old_id:
			lurk_counter[0] += 1
			threshold = random.randint(2,4)
			print(f'lurk threshold: {threshold}')
			
			if lurk_counter[0] >= threshold and message.channel.category_id == 464812325527093258:
				lurk_counter[0] = 0
				bot.loop.create_task(lurk_respond(message))
		else:
			lurk_counter[0] = 1
		print(f'lurk counter: {lurk_counter}')


async def lurk_respond(message:discord.Message):
	sleep_time = random.randint(15,300)
	print(f'lurk sleep for {sleep_time}')
	await asyncio.sleep(sleep_time)

	last_message = await message.channel.history(limit=1).flatten()
	if message.author == last_message[0].author:

		key = f'lurk_{message.channel.id}'
		async with message.channel.typing():
			typing_time = random.randint(1,5)
			print(f'lurk typing for {typing_time}')
			await asyncio.sleep(typing_time)
			await send_response(message.channel, [key])
	else:
		print(f'lurk fail {last_message[0].author} answered first')


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
			if master["index"] < len(master["reminders"]) and not master["asking"]:
				master_delta = master["reminders"][master["index"]]["time"] - t

				print(f"id:{master['id']}, master_delta: {master_delta}, delta:{delta}")
				if not master['wait'] and master_delta > 0:
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
async def bully(ctx:Context):
	users = []
	for i in masters:
		if ctx.message.author.id != i["id"]:
			users.append(f'<@{i["id"]}>')
	await ctx.send(f'nyaa!! {random.choice(users)} 😿 help me pls!!!')


@bot.command(name='img')
async def img(ctx:Context):
	await delete_user_message(ctx.message)
	embed = discord.Embed()
	embed.set_image(url = random.choice(linkdatabase.armpitst))
	await ctx.send(embed=embed)
	pass


@bot.command(help='adds a reminder to your list \nfor best result use imperative mood', usage='08:00 make coffee')
async def add(ctx:Context, _time:str, *_name:str):

	channel = ctx.channel
	# users id
	id = ctx.message.author.id

	master = get_master(id)

	# if user isn't a master, create a new master from a template and assign users id
	if master is None:
		master = deepcopy(TEMP_MASTER)
		master["id"] = id
		masters.append(master)
		print(f"created new master with id {id}")

	# add a new activity and save, returns list with index, time, name
	l = reminder_add(master, _time, _name)
	data_save()

	update_restart()

	item = RESPONSES['add_item'].format(*tuple(l))
	block = format_block(ctx, 'add_block', item)

	await delete_user_message(ctx.message)

	await send_response(channel, ['add', 'hello', 'activity', 'tasks', 'end'], [block])


@bot.command(name='list', help='shows your list of reminders')
async def _list(ctx:Context):

	channel = ctx.channel
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
		block = format_block(ctx, 'list_block', '\n'.join(items))

		await delete_user_message(ctx.message)

		await send_response(channel, ['list', 'hello', 'tasks', 'end'], [block])
	else:
		await send_response(channel, ['list_no', 'hello', 'tasks'])


@bot.command(help='removes element from your list by index')
async def remove(ctx:Context, index:int):

	channel = ctx.channel
	master = get_master(ctx.message.author.id)
	length = len(master["reminders"])

	# check if list is not empty
	if master is not None and length > 0:

		# check index validity
		if 0 <= index < length:

			# set back index if removed activity already happend
			if master["index"] > index and master["index"] != 0:
				master["index"] -= 1

			activity = master["reminders"].pop(index)
			item = RESPONSES['remove_item'].format(
				index,
				seconds_to_time(activity["time"]),
				activity["name"]
			)

			# format into code block
			block = format_block(ctx, 'remove_block', item)

			data_save()

			update_restart()

			await delete_user_message(ctx.message)
			
			await send_response(channel, ['remove', 'hello', 'activity', 'tasks'], [block])
		else:
			await send_response(channel, ['denied'])
	else:
		await send_response(channel, ['list_no', 'hello', 'tasks'])


@bot.command(help='clears your list')
async def removeall(ctx:Context):

	channel = ctx.channel
	master = get_master(ctx.message.author.id)

	# check if list is not empty
	if master is not None and len(master["reminders"]) > 0:
		items = []

		# append all masters reminders
		for i in range(0, len(master["reminders"])):
			activity = master["reminders"][i]

			items.append(RESPONSES['remove_item'].format(
				i,
				seconds_to_time(activity["time"]),
				activity["name"]))
		
		# format into code block
		block = format_block(ctx, 'remove_block', '\n'.join(items))

		master["reminders"].clear()
		data_save()

		update_restart()

		await delete_user_message(ctx.message)

		await send_response(channel, ['remove', 'hello', 'remove_all', 'tasks'], [block])
	else:
		await send_response(channel, ['list_no', 'hello', 'tasks'])


@bot.command(help='gets value property from your config', usage='snooze')
async def get(ctx:Context, key:str):

	channel = ctx.channel
	master = get_master(ctx.message.author.id)

	if master is not None and key in master:
		# format into code block
		block = format_block(ctx, 'get_block', key, master[key])

		await delete_user_message(ctx.message)

		await send_response(channel, ['get', 'hello'], [block])
	else:
		await send_response(channel, ['denied'])


@bot.command(name='set', help='sets value property for your config', usage='snooze 600')
async def _set(ctx:Context, key:str, *value):

	channel = ctx.channel
	master = get_master(ctx.message.author.id)
	value_string = " ".join(value)
	value_new = eval(value_string)

	if master is not None and key in master and type(master[key]) == type(value_new):
		old = master[key]
		master[key] = value_new
		update_restart()

		# format into code block
		block = format_block(ctx, 'set_block', key, old, value_string)

		await delete_user_message(ctx.message)

		await send_response(channel, ['set', 'hello'], [block])
	else:
		await send_response(channel, ['denied'])


@bot.command()
async def stop(ctx:Context):
	if ctx.message.author.id == 204981328305848330 or ctx.message.author.id == 270603696683876352:
		bot.loop.stop()
	else:
		await ctx.send("nice try smartest")


@atexit.register
def exit_handler():
	print("stopping maid bot.\n")


async def delete_user_message(message:discord.Message):
	if message.guild is not None:
		await message.delete()


def reminder_cancel(master_id):
	for reminder in reminders:
		if reminder[0] == master_id:
			reminder[1].cancel()
			reminders.remove(reminder)
			break


def reminder_start(master, late=False, delay=False):
	task = bot.loop.create_task(ask(master, late, delay))
	id = master["id"]
	new_reminder = [id, task]
	reminders.append(new_reminder)


async def reminder_next(master):

	user = bot.get_user(master['id'])

	master['index'] += 1
	master['asking'] = False
	master['message'] = 0

	reminder_cancel(master['id'])

	if master['index'] == len(master['reminders']) and master['wait']:
		master['wait'] = False
		master['index'] = 0

	data_save()
	update_restart()

	await send_response(user, ['congrats', 'emoji'])


async def ask(master, late=False, delay=False):
	print(f'active reminders:\n{reminders}')

	if delay:
		await asyncio.sleep(master['snooze'])

	sorry = ""
	if late:
		sorry = random.choice(RESPONSES['late']) + " "
	activity = master["reminders"][master["index"]]["name"]
	user = bot.get_user(master['id'])

	message = await send_response(user, ['ask', 'hello'], [sorry, activity])
	master['message'] = message.id
	
	data_save()
	
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

	await asyncio.sleep(master['snooze'])

	master['message'] = 0
	data_save()

	await message.delete()
	await ask(master)


async def snooze(master):

	user = bot.get_user(master['id'])
	text = f"{int(master['snooze'] / 60)} minutes"

	await send_response(user, ['snooze'], [text])

	reminder_cancel(master["id"])
	await asyncio.sleep(master['snooze'])

	reminder_start(master)


async def send_response(channel, keys, texts=[]) -> discord.Message:
	sequence = []
	for key in keys:
		sequence.append(random.choice(RESPONSES[key]))
	sequence += texts
	main = sequence.pop(0)
	
	return await channel.send(main.format(*tuple(sequence)))


def format_block(ctx:Context, key, *items):
	return RESPONSES[key].format(ctx.message.author.display_name, *items)


def get_master(id):
	for master in masters:
		if master["id"] == id:
			return master
	return None


async def get_master_message(master) -> discord.Message:
	if master['message'] == 0:
		return None
	
	user = bot.get_user(master['id'])
	return await user.fetch_message(master['message'])


def reminder_add(master, _time, _name):

	# create a new activity from a template
	new_activity = deepcopy(TEMP_REMINDER)

	time = max(0, min(time_to_seconds(_time), 86340))
	name = " ".join(_name)
	ask = time > get_seconds()

	new_activity["time"] = time
	new_activity["name"] = name
	
	length = len(master['reminders'])
	index = length
	for i in range(0, length):
		if master["reminders"][i]["time"] > new_activity["time"]:
			index = i
			break

	# add activity to the master reminders array
	if master['index'] > index or master['index'] == index and not ask:
		master['index'] += 1
	master['reminders'].insert(index, new_activity)

	print (f"added new activity for master {master['id']} {new_activity}")
	return [index, seconds_to_time(time), name]


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
