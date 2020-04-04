import discord
import atexit
import time
import json
import asyncio
import random

from discord.ext import commands
from datetime import datetime
from copy import deepcopy

jsonfile = "data.json"
token = "NDk0NTU5MDU3MTUyMzExMjk2.XntWMA.tdBff92dd0O5I-4mMR_3MxJw69A"
prefix = "."

bot = commands.Bot(command_prefix=prefix)

update_task = None

responses = []

date = None

masters = []
master_template = {"id":0, "activities":[], "index":0, "wait":False}
activity_template = {"time":0, "name":""}

snooze_time = 600
late_threshold_time = 300

responses_greeting = [
	"nyaa!",
	"nyaa! nyaa!",
	"nyaa! nyaa! nyaa!",
	"nyaa! nyaa! nyaa! nyaa!",
	"nyaa! nyaa! nyaa! nyaa! nyaa!",
	"master!",
	"ma... master!",
	"ohayoo!",
	"domo!",
	"hey!",
	"hey loser!",
	"yo!",
	"yo nigga!",
	"whaddup!",
	"whaddup zoomer!",
	"whaddup dude!",
	"whaddup nigga!",
	"dude!",
	"hello there!",
	"greetings mortal!",
	"ahoj moj!"
]

responses_ask = [
	"{0} {2}did you {1}?",
	"{0} {2}am here to remind you to {1}",
	"{0} {2}did you {1} already?",
	"{0} {2}please tell me that you {1} already",
	"{0} {2}please tell me that you didn't forgot to {1}",
	"{0} {2}am here to remind you to do the thing",
	"{0} {2}am here to remind you about the thing",
	"{0} {2}did you do the thing already?",
	"{0} {2}hope you didn't forgot to do the thing",
	"{0} {2}hope you didn't forgot about the thing",
	"{2}did you {1}?",
	"{2}am here to remind you to {1}",
	"{2}did you {1} already?",
	"{2}please tell me that you {1} already",
	"{2}please tell me that you didn't forgot to {1}",
	"{2}did you do the thing already?",
	"are you done now?",
	"are you done?",
	"done now?",
	"done?",
	"vibe check 🔫",
	"yes?"
]

responses_late = [
	"sorry for being late!",
	"sowwy fow being wate!",
	"am so sorry for being late!",
	"am sorry for being so late!",
	"yes am late, sorry",
	"yes am late, am sorry",
	"please forgive me for being so late!",
	"please forgive me for being so late! 🙏",
	"please forgive me for being so late! it won't happen again i swear!",
	"forgive me for being so late!",
	"forgive me for being late!",
	"don't ask me why am late",
	"sorry to keep you waiting!",
	"sorry to have kept you waiting!",
	"sorry for keeping you waiting!",
	"sorry for having kept you waiting!",
	"kept ya waitin' huh?"
]

responses_congrats = [
	"omedetou {}",
	"congratulations {}",
	"congrats {}",
	".{}",
	"quieres {}",
	"bro {}",
	"bruh {}",
	"my man {}",
	"nice dick {}",
	"nice cock {}",
	"conglaturations {}",
	"yo, yoooo!!! {}",
	"yay!!! {}",
	"am glad you're doing ok! {}",
	"am glad! {}",
	"keep it up man! {}",
	"keep it up! {}",
	"ok {}",
	"good job my guy",
]

responses_emoji = [
	"👏",
	"👏👏",
	"👏👏👏",
	"👏👏👏👏",
	"👏👏👏👏👏",
	"👏👏👏👏👏👏",
	""
]

responses_snooze = [
	"i'll come back in {}",
	"i'll come back in like {}",
	"i'll come back in about {}",
	"i'll be back in {}",
	"i'll be back in like {}",
	"i'll be back in about {}",
	"i'll give you {}",
	"i'll give you like {}",
	"i'll give you like {}, make it quick",
	"i'll be back 🤖",
	"ama be back in {}",
	"ama be back in like {}",
	"ama be back in about {}",
	"i back in {}",
	"wait {}",
	"you better finish before i come back",
	"you better be done when i come back",
	"whatever, not like i care",
	"whatever",
	"go die",
	"die"
]

responses_add = [
	"{0} i added {1} to your {2}! {3}",
	"{0} i have added {1} to your {2}! {3}",
	"{0} i added {1} to your {2}!",
	"{0} i have added {1} to your {2}!",
	"i added {1} to your {2}! {3}",
	"i have added {1} to your {2}! {3}",
	"i added {1} to your {2}!",
	"i have added {1} to your {2}!"
]

responses_activity = [
	"this",
	"this activity",
	"this task",
	"this reminder",
	"the activity",
	"the task",
	"the reminder"
]

responses_tasks = [
	"list",
	"list of activities",
	"list of tasks",
	"list of reminders"
]

responses_end = [
	"thank you for your service!",
	"arigato gozaimashita!",
	"thank you!",
	"arigato!",
	"thanks!",
	"thank",
	"happy?",
	"feel free to use me again",
	"feel free to use me again 😏",
	"me too thanks",
	"me too"
]

responses_list = [
	"{0} here is your {1}!{2}",
	"{0} here is your {1}! {3}{2}",
	"here is your {1} {0}{2}",
	"here is your {1}! {3}{2}",
	"here is your {1}!{2}"
]

responses_nolist = [
	"{0} sorry but there doesn't seem to be anything on your {1}",
	"{0} sorry but there doesn't seem to be anything",
	"{0} sorry but there isn't anything on your {1}",
	"{0} sorry but there isn't anything",
	"{0} sorry but there doesn't seem to be anything on your {1}, please conscider creating a reminder!",
	"{0} sorry but there doesn't seem to be anything on your {1}, please conscider creating a reminder! please you won't regret it i swear!",
	"{0} sorry but there doesn't seem to be anything on your {1}, please conscider creating a reminder! please you won't regret it i swear! onegai!",
	"{0} sorry but there doesn't seem to be anything, please conscider creating a reminder!",
	"{0} sorry but there isn't anything on your {1}, please conscider creating a reminder!",
	"{0} sorry but there isn't anything, please conscider creating a reminder!",
	"sorry but there doesn't seem to be anything on your {1}",
	"sorry but there doesn't seem to be anything",
	"sorry but there isn't anything on your {1}",
	"sorry but there isn't anything",
	"sorry, create a reminder first",
	"create a reminder first",
	"create a reminder first, you dumbass",
	"create a reminder first, you smartass",
	"don't waste my time, you don't have a list",
	"don't waste my time, you knew you don't have a list",
	"don't waste my time, you know you don't have anything on your list",
	"don't waste my time, you know that you don't have anything on your list",
	"fuck off"
]

responses_remove = [
	"{0} i have removed {1} from your {2}!",
	"{0} i removed {1} from your {2}!",
	"i have removed {1} from your {2}!",
	"i removed {1} from your {2}!",
	"i have removed {1} from your {2} {0}",
	"i removed {1} from your {2} {0}",
	"done! {0}",
	"done {0}",
	"done!"
]


@bot.event
async def on_ready():
	# load all masters and their activities from json
	await bot.change_presence(activity=discord.Game("with copy.deepcopy()"))
	data_load()

	update_restart()
	print("maid bot is ready.\n")


@bot.event
async def on_reaction_add(reaction, user):
	if reaction.me and reaction.count > 1:
		# remove reactions
		await reaction.message.remove_reaction("✅", bot.user)
		await reaction.message.remove_reaction("⏰", bot.user)

		master = get_master(user.id)
		if reaction.emoji == "✅": # iterate index
			master["index"] = master["index"] + 1
			master["wait"] = False
			data_save()
			update_restart()
			await master_congratulate(master)
		elif reaction.emoji == "⏰": # ask again after snooze
			bot.loop.create_task(master_snooze(master))


async def update():
	await bot.wait_until_ready()

	alarms = []
	while not bot.is_closed():

		global date
		if date.day != datetime.now().day:
			date = datetime.now()
			for master in masters:
				master["index"] = 0
				master["wait"] = False
			print("new day activities index reset")
			data_save()

		t = datetime.now().hour * 3600 + datetime.now().minute * 60 + datetime.now().second
		delta = 86400 - t # time till midnight

		# find smallest delta
		for master in masters:
			if (master["index"] < len(master["activities"]) and not master["wait"]):
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
			data_save()
			#response_wait(master, late)
			bot.loop.create_task(master_ask(master, late))
			# await master_ask(master, late)

		# continue loop after delta seconds
		print(f"sleep for {delta}")
		await asyncio.sleep(delta)


def update_restart(): # restart update loop
	global update_task
	if update_task != None:
		update_task.cancel()
	update_task = bot.loop.create_task(update())


@bot.command()
async def bully(ctx):  # calls all masters for help
	users = []
	for i in masters:
		if not ctx.message.author.id == i["id"]:
			users.append("<@{}>".format(i["id"]))
	await ctx.send("nyaa!! {} 😿 help me pls!!!".format(random.choice(users)))


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
		items = []
		for i in range(0, len(master["activities"])):
			items.append("{}. {}".format(i, activity_text(master["activities"][i])))
		text = "\n```fix\n{}```".format('\n'.join(items))
		await master_list(ctx, text)
	else:
		await master_nolist(ctx)


@bot.command()
async def remove(ctx, index:int):
	master = get_master(ctx.message.author.id)
	if master is not None and len(master["activities"]) > 0:
		index %= len(master["activities"])
		if master["index"] >= index:
			length = len(master["activities"])

	if master != None and length > 0:
		index %= length
		if master["index"] >= index and master["index"] != 0: # set back index if removed activity already happend
			master["index"] -= 1
		activity = master["activities"].pop(index)
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
		await ctx.send("nice try smartass")


@atexit.register
def exit_handler():
	print("stopping maid bot.")


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
	if index == master["index"]:
		await message.delete()
		await master_ask(master)


async def master_congratulate(master):
	emoji = random.choice(responses_emoji)
	await bot.get_user(master["id"]).send(random.choice(responses_congrats).format(emoji))


async def master_snooze(master):
	t = f"{int(snooze_time / 60)} minutes"
	await bot.get_user(master["id"]).send(random.choice(responses_snooze).format(t))
	await asyncio.sleep(snooze_time)
	bot.loop.create_task(master_ask(master))


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
	if index != None:
		if master["index"] > index or master["index"] == index and not ask:
			master["index"] += 1
		master["activities"].insert(i, new_activity)
	else:
		if master["index"] == len(master["activities"]) and not ask:
			master["index"] += 1
		master["activities"].append(new_activity)
	print (f"added new activity for master {master['id']} {new_activity}")


def activity_text(activity):
	return "{} {}".format(seconds_to_time(activity["time"]), activity["name"])


def time_to_seconds(time_string):
	h, m = time_string.split(":")
	return int(h) * 3600 + int(m) * 60


def seconds_to_time(seconds):
	return time.strftime("%H:%M", time.gmtime(seconds))


def data_save():
	save_data = {"date":date.strftime("%Y/%m/%d"), "masters":masters}

	with open(jsonfile, 'w') as fp:
		json.dump(save_data, fp, indent="\t")
		print("saved data to json")


def data_load():
	with open(jsonfile) as fp:
		jsondata = json.load(fp)

		global date

		date_string = jsondata["date"]
		y, m, d = date_string.split("/")
		date = datetime(int(y), int(m), int(d))

		for i in jsondata["masters"]:
			masters.append(i)

		print("loaded data from json")


bot.run(token)
