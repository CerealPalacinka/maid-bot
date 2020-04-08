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
TEMP_MASTER = dict(id=0, reminders=[], index=0, asking=False, wait=False)
TEMP_REMINDER = dict(time=0, name='')

SNOOZE_TIME = 600
LATE_THRESHOLD_TIME = 300

date = None

update_task = None
reminders = []

masters = []


@bot.event
async def on_ready():
	# load all masters and their reminders from json
	await bot.change_presence(activity=discord.Game("with copy.deepcopy()"))
	data_load()

	for master in masters:
		master['asking'] = False
		if master['wait']:
			reminder_start(master, True)

	update_restart()
	print("maid bot is ready.\n")


@bot.event
async def on_reaction_add(reaction, user):
	if reaction.me and reaction.count > 1:
		# remove reactions
		await reaction.message.remove_reaction("✅", bot.user)
		await reaction.message.remove_reaction("⏰", bot.user)

		master = get_master(user.id)
		if reaction.emoji == "✅":  # iterate index
			master['index'] += 1
			master['asking'] = False

			reminder_cancel(master["id"])

			if master['index'] == len(master['reminders']) and master['wait']:
				master['wait'] = False
				master['index'] = 0

			data_save()
			update_restart()
			await master_congratulate(master)
		elif reaction.emoji == "⏰":  # ask again after snooze
			bot.loop.create_task(master_snooze(master))


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

	await master_add(ctx)


@bot.command(name='list', help='shows your list of reminders')
async def _list(ctx):

	master = get_master(ctx.message.author.id)
	if master is not None and len(master["reminders"]) > 0:

		# start with masters name
		items = [ctx.message.author.display_name]

		# append all masters reminders
		for i in range(0, len(master["reminders"])):
			activity = master["reminders"][i]
			items.append(f'{i}. {seconds_to_time(activity["time"])} {activity["name"]}')

		# format into code block
		n = '\n'
		await master_list(ctx, f'{n}```fix{n}{n.join(items)}```')
	else: 
		await master_nolist(ctx)


@bot.command(help='removes element from your list by index')
async def remove(ctx, index:int):
	master = get_master(ctx.message.author.id)
	if master is not None and len(master["reminders"]) > 0:
		index %= len(master["reminders"])
		if master["index"] >= index:
			length = len(master["reminders"])

	if master is not None and length > 0:
		index %= length
		if master["index"] > index and master["index"] != 0:  # set back index if removed activity already happend
			master["index"] -= 1
		master["reminders"].pop(index)
		data_save()

		update_restart()

		await master_remove(ctx)
	else:
		await master_nolist(ctx)


@bot.command(help='clears your list')
async def removeall(ctx):
	master = get_master(ctx.message.author.id)
	if master is not None and len(master["reminders"]) > 0:
		master["reminders"].clear()
		data_save()

		update_restart()

		await master_remove(ctx)
	else:
		await master_nolist(ctx)


@bot.command()
async def stop(ctx):
	if ctx.message.author.id == 204981328305848330 or ctx.message.author.id == 270603696683876352:
		bot.loop.stop()
	else:
		await ctx.send("nice try smartest")


@atexit.register
async def exit_handler():
	print("stopping maid bot.")


def reminder_cancel(master_id):
	for reminder in reminders:
		if reminder[0] == master_id:
			reminder[1].cancel()
			reminders.remove(reminder)
			break


def reminder_start(master, late=False):
	task = bot.loop.create_task(master_ask(master, late))
	id = master["id"]
	new_reminder = [id, task]
	reminders.append(new_reminder)


async def master_ask(master, late=False):
	index = master["index"]
	sorry = ""
	if late:
		sorry = random.choice(RESPONSES['late']) + " "
	greeting = random.choice(RESPONSES['greeting'])
	activity = master["reminders"][index]["name"]
	message = await bot.get_user(master["id"]).send(random.choice(RESPONSES['ask']).format(greeting, activity, sorry))
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

	await asyncio.sleep(SNOOZE_TIME)
	await message.delete()
	await master_ask(master)


async def master_congratulate(master):
	emoji = random.choice(RESPONSES['emoji'])
	await bot.get_user(master["id"]).send(random.choice(RESPONSES["congrats"]).format(emoji))


async def master_snooze(master):
	t = f"{int(SNOOZE_TIME / 60)} minutes"
	await bot.get_user(master["id"]).send(random.choice(RESPONSES['snooze']).format(t))

	reminder_cancel(master["id"])
	await asyncio.sleep(SNOOZE_TIME)

	reminder_start(master)


async def master_add(ctx):
	greeting = random.choice(RESPONSES['greeting'])
	activity = random.choice(RESPONSES['activity'])
	tasks = random.choice(RESPONSES['tasks'])
	end = random.choice(RESPONSES['end'])
	await ctx.send(random.choice(RESPONSES['add']).format(greeting, activity, tasks, end))


async def master_list(ctx, text):
	if ctx.guild is not None:  # delete users message unless in DM channel
		await ctx.message.delete()

	greeting = random.choice(RESPONSES['greeting'])
	tasks = random.choice(RESPONSES['tasks'])
	end = random.choice(RESPONSES['end'])

	await ctx.send(random.choice(RESPONSES['list']).format(greeting, tasks, text, end))


async def master_nolist(ctx):
	greeting = random.choice(RESPONSES['greeting'])
	tasks = random.choice(RESPONSES['tasks'])
	await ctx.send(random.choice(RESPONSES['nolist']).format(greeting, tasks))


async def master_remove(ctx):
	greeting = random.choice(RESPONSES['greeting'])
	activity = random.choice(RESPONSES['activity'])
	tasks = random.choice(RESPONSES['tasks'])
	await ctx.send(random.choice(RESPONSES['remove']).format(greeting, activity, tasks))


def get_master(id):
	for master in masters:
		if master["id"] == id:
			return master
	return None


def reminder_add(master, ctx, _time, _name):
	# create a new activity from a template
	new_activity = deepcopy(TEMP_REMINDER)

	t = time_to_seconds(_time)
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
	with open(FP_DATA) as fp:
		jsondata = json.load(fp)

		global date
		date_list = jsondata["date"]
		y, m, d = date_list[0], date_list[1], date_list[2]
		date = datetime(y, m, d)

		global masters
		masters = jsondata["masters"]

	with open(FP_RESPONSES) as fp:
		global RESPONSES
		RESPONSES = json.load(fp)

	print("loaded data from json")

bot.run(os.getenv('DISCORD_TOKEN'))
