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


file_data = "data.json"
file_responses = "responses.json"

load_dotenv()
bot = commands.Bot(command_prefix=os.getenv('DISCORD_PREFIX'))

update_task = None

responses = []

date = None

masters = []
master_template = dict(id=0, activities=[], index=0, wait=False)
activity_template = dict(time=0, name="")

snooze_time = 600
late_threshold_time = 300

responses_greeting = []
responses_ask = []
responses_late = []
responses_congrats = []
responses_emoji = []
responses_snooze = []
responses_add = []
responses_activity = []
responses_tasks = []
responses_end = []
responses_list = []
responses_nolist = []
responses_remove = []

@bot.event
async def on_ready():
	# load all masters and their activities from json
	await bot.change_presence(activity=discord.Game("with copy.deepcopy()"))
	data_load()

	for master in masters:
		master["wait"] = False

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
			master["index"] = master["index"] + 1
			master["wait"] = False

			response_cancel(master["id"])

			data_save()
			update_restart()
			await master_congratulate(master)
		elif reaction.emoji == "⏰":  # ask again after snooze
			bot.loop.create_task(master_snooze(master))


async def update():
	await bot.wait_until_ready()

	while not bot.is_closed():

		global date
		if date.day != datetime.now().day:
			date = datetime.now()
			for master in masters:
				master["index"] = 0
				master["wait"] = False
				response_cancel(master["id"])
			print("new day activities index reset")
			data_save()

		t = datetime.now().hour * 3600 + datetime.now().minute * 60 + datetime.now().second
		delta = 86400 - t  # time till midnight

		alarms = []
		# find smallest delta
		for master in masters:
			if master["index"] < len(master["activities"]) and not master["wait"]:
				master_delta = master["activities"][master["index"]]["time"] - t

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
			late = abs(alarm[1]) > late_threshold_time

			print(f"alarm id:{master['id']} late: {late}")

			master["wait"] = True

			response_create(master, late)

		data_save()

		# continue loop after delta seconds
		print(f"sleep for {delta}")
		await asyncio.sleep(delta)


def update_restart(): # restart update loop
	global update_task
	if update_task is not None:
		update_task.cancel()
	update_task = bot.loop.create_task(update())


@bot.command()
async def bully(ctx):  # calls all masters for help
	users = []
	for i in masters:
		if ctx.message.author.id != i["id"]:
			users.append(f"<@{i['id']}>")
			print(users)
	await ctx.send(f"nyaa!! {random.choice(users)} 😿 help me pls!!!")

@bot.command(name='img')
async def img(ctx):
	await ctx.message.delete()
	embed = discord.Embed()
	embed.set_image(url = random.choice(linkdatabase.armpitst))
	await ctx.send(embed=embed)
	pass

@bot.command()
async def test (ctx, _time:str, *_name:str):
	await ctx.send(f'time: {_time} name: {" ".join(_name)}')

@bot.command()
async def add(ctx, *args):  # add activity command, argument time of day in HH:MM and name of the activity
	# users id
	id = ctx.message.author.id

	master = None
	for i in masters:
		if i["id"] == id:
			master = i
			break

	# if user isn't a master, create a new master from a template and assign users id
	if master is None:
		master = deepcopy(master_template)
		master["id"] = id
		masters.append(master)
		print(f"created new master with id {id}")

	# add a new activity and save
	activity_add(master, ctx, args)
	data_save()

	update_restart()

	await master_add(ctx)


@bot.command(aliases=["list", "activities", "tasks"])
async def _list(ctx):

	master = get_master(ctx.message.author.id)
	if master is not None and len(master["activities"]) > 0:

		# start with masters name
		items = [ctx.message.author.display_name]

		# append all masters activities
		for i in range(0, len(master["activities"])):
			activity = master["activities"][i]
			items.append(f'{i}. {seconds_to_time(activity["time"])} {activity["name"]}')

		# format into code block
		n = '\n'
		await master_list(ctx, f'{n}```fix{n}{n.join(items)}```')
	else: 
		await master_nolist(ctx)


@bot.command()
async def remove(ctx, index:int):
	master = get_master(ctx.message.author.id)
	if master is not None and len(master["activities"]) > 0:
		index %= len(master["activities"])
		if master["index"] >= index:
			length = len(master["activities"])

	if master is not None and length > 0:
		index %= length
		if master["index"] >= index and master["index"] != 0: # set back index if removed activity already happend
			master["index"] -= 1
		master["activities"].pop(index)
		data_save()

		update_restart()

		await master_remove(ctx)
	else:
		await master_nolist(ctx)


@bot.command()
async def removeall(ctx):
	master = get_master(ctx.message.author.id)
	if master is not None and len(master["activities"]) > 0:
		master["activities"].clear()
		data_save()

		update_restart()

		await master_remove(ctx)
	else:
		await master_nolist(ctx)


@bot.command()
async def intro(ctx, id: int):
	if ctx.message.author.id == 204981328305848330:
		await bot.get_channel(id).send(
			"su... sumimasendesuka!\n"
			"am your new maid bot! yoroshiku onegaishimasu!\n"
			"my puwpose is to remind you to do things on a daily basis!\n"
			"if u want to use me😏, type '.add <time of day in HH:MM format> "
			"<description of what you want to do at that specific time that you want to be remided of>'\n"
			"sexample: .add 09:30 make coffee\n"
			"and after that ill sednd you a dm at 9:30 to remind you to make a coffeee\n"
			"with the comand .list you can keep trac of all your reminders,"
			" if you want to remove a reminder just look up the index of the"
			" reminder you want to delet with .list, "
			"and type '.remove <index of ther eminder u want to annihilate>' an dpress enter.\n"
			"am i cleare with everyone? u don't need to use my services, but please consciddre\nthanky ou for having me!")


@bot.command()
async def stop(ctx):
	if ctx.message.author.id == 204981328305848330 or ctx.message.author.id == 270603696683876352:
		bot.loop.stop()
	else:
		await ctx.send("nice try smartest")


@atexit.register
async def exit_handler():
	print("stopping maid bot.")


def response_cancel(master_id):
	for response in responses:
		if response[0] == master_id:
			response[1].cancel()
			responses.remove(response)
			break

def response_create(master, late=False):
	task = bot.loop.create_task(master_ask(master, late))
	id = master["id"]
	new_response = [id, task]
	responses.append(new_response)

async def master_ask(master, late=False):
	index = master["index"]
	sorry = ""
	if late:
		sorry = random.choice(responses_late) + " "
	greeting = random.choice(responses_greeting)
	activity = master["activities"][index]["name"]
	message = await bot.get_user(master["id"]).send(random.choice(responses_ask).format(greeting, activity, sorry))
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

	await asyncio.sleep(snooze_time)
	await message.delete()
	await master_ask(master)


async def master_congratulate(master):
	emoji = random.choice(responses_emoji)
	await bot.get_user(master["id"]).send(random.choice(responses_congrats).format(emoji))


async def master_snooze(master):
	t = f"{int(snooze_time / 60)} minutes"
	await bot.get_user(master["id"]).send(random.choice(responses_snooze).format(t))

	response_cancel(master["id"])
	await asyncio.sleep(snooze_time)

	response_create(master)


async def master_add(ctx):
	greeting = random.choice(responses_greeting)
	activity = random.choice(responses_activity)
	tasks = random.choice(responses_tasks)
	end = random.choice(responses_end)
	await ctx.send(random.choice(responses_add).format(greeting, activity, tasks, end))


async def master_list(ctx, text):
	greeting = random.choice(responses_greeting)
	tasks = random.choice(responses_tasks)
	end = random.choice(responses_end)
	await ctx.message.delete()
	await ctx.send(random.choice(responses_list).format(greeting, tasks, text, end))


async def master_nolist(ctx):
	greeting = random.choice(responses_greeting)
	tasks = random.choice(responses_tasks)
	await ctx.send(random.choice(responses_nolist).format(greeting, tasks))


async def master_remove(ctx):
	greeting = random.choice(responses_greeting)
	activity = random.choice(responses_activity)
	tasks = random.choice(responses_tasks)
	await ctx.send(random.choice(responses_remove).format(greeting, activity, tasks))


def response_wait(master, late=False):
	bot.loop.create_task(master_ask(master, late))
	pass


def get_wait(master, index):
	for item in responses:
		if item[0] == master and item[1] == index:
			return item
	return None

def get_master(id):
	for i in masters:
		if i["id"] == id:
			return i
	return None


def activity_add(master, ctx, args):
	# create a new activity from a template
	new_activity = deepcopy(activity_template)

	t = time_to_seconds(args[0])
	ask = t > datetime.now().hour * 3600 + datetime.now().minute * 60

	new_activity["time"] = t
	new_activity["name"] = " ".join(args[1:])

	index = None
	for i in range(0, len(master["activities"])):
		if master["activities"][i]["time"] > new_activity["time"]:
			index = i
			break

	# add activity to the master activities array
	if index is not None:
		if master["index"] > index or master["index"] == index and not ask:
			master["index"] += 1
		master["activities"].insert(i, new_activity)
	else:
		if master["index"] == len(master["activities"]) and not ask:
			master["index"] += 1
		master["activities"].append(new_activity)
	print (f"added new activity for master {master['id']} {new_activity}")

def time_to_seconds(time_string):
	h, m = time_string.split(":")
	return int(h) * 3600 + int(m) * 60


def seconds_to_time(seconds):
	return time.strftime("%H:%M", time.gmtime(seconds))


def data_save():
	out = [date.year, date.month, date.day]
	save_data = dict(date=out, masters=masters)

	with open(file_data, 'w') as fp:
		json.dump(save_data, fp, indent="\t")
		print("saved data to json")


def data_load():
	with open(file_data) as fp:
		jsondata = json.load(fp)

		global date

		date_list = jsondata["date"]
		y, m, d = date_list[0], date_list[1], date_list[2]
		date = datetime(y, m, d)

		for i in jsondata["masters"]:
			for master in masters:
				if master == i:
					print("duplicate master")
			if i not in masters:
				masters.append(i)

	with open(file_responses) as fp:
		json_responses = json.load(fp)
		global responses_greeting, responses_remove, responses_nolist, responses_list,responses_end, responses_tasks, responses_activity, responses_snooze,responses_emoji, responses_congrats
		responses_greeting = json_responses["greeting"]
		responses_ask      = json_responses["ask"]
		responses_late     = json_responses["late"]
		responses_congrats = json_responses["congrats"]
		responses_emoji    = json_responses["emoji"]
		responses_snooze   = json_responses["snooze"]
		responses_add      = json_responses["add"]
		responses_activity = json_responses["activity"]
		responses_tasks    = json_responses["tasks"]
		responses_end      = json_responses["end"]
		responses_list     = json_responses["list"]
		responses_nolist   = json_responses["nolist"]
		responses_remove   = json_responses["remove"]

	print("loaded data from json")

bot.run(os.getenv('DISCORD_TOKEN'))
