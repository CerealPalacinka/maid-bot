import discord, atexit, time, json, asyncio, random
from discord.ext import commands
from datetime import datetime
from copy import deepcopy

jsonfile = "data.json"
token = "NDk0NTU5MDU3MTUyMzExMjk2.XntWMA.tdBff92dd0O5I-4mMR_3MxJw69A"
prefix = "."

bot = commands.Bot(command_prefix=prefix)

update_task = None

date = None

masters = []
master_template = {"id":0, "activities":[], "index":0}
activity_template = {"time":0, "name":""}

snooze_time = 1

@bot.event
async def on_ready():
	# load all masters and their activities from json
	await bot.change_presence(activity=discord.Game("with copy.deepcopy()"))
	data_load()

	global date
	if date.day != datetime.now().day:
		date = datetime.now()
		for master in masters:
			master["index"] = 0
		print("new day activities index reset")
		data_save()

	update_restart()
	print("maid bot is ready.\n")

@bot.event
async def on_reaction_add(reaction, user):
	if reaction.me and reaction.count > 1:
		# remove reactions
		await reaction.message.remove_reaction("✅", bot.user)
		await reaction.message.remove_reaction("⏰", bot.user)

		master = get_master(user.id)
		if reaction.emoji == "✅":
			master["index"] = (master["index"] + 1) % len(master["activities"])
			data_save()
			await master_congratulate(master)
			update_restart()
		elif reaction.emoji == "⏰":
			await asyncio.sleep(snooze_time)
			await master_ask(master)

async def update():
	await bot.wait_until_ready()

	masters_to_alert = []
	while not bot.is_closed():

		t = datetime.now().hour * 3600 + datetime.now().minute * 60
		delta = t

		# find smallest delta
		for master in masters:
			master_delta = master["activities"][master["index"]]["time"] - t
			
			print(f"id:{master['id']}, master_delta: {master_delta}, delta:{delta}")
			if master_delta < delta:
				if master_delta > 0:
					delta = master_delta
				else:
					# if delta is below zero add master to alert list
					masters_to_alert.append(master)

		# alert all masters
		for alarm in masters_to_alert:
			print(f"alarm id:{alarm['id']}")
			await master_ask(alarm)

		# continue loop after delta seconds
		print(f"sleep for {delta}")
		await asyncio.sleep(delta)

@bot.command()
async def bully(ctx): # calls all masters for help
	users = []
	for i in masters:
		if not ctx.message.author.id == i["id"]:
			users.append("<@{}>".format(i["id"]))
	await ctx.send("nyaa!! {} 😿 help me pls!!!".format(random.choice(users)))

@bot.command()
async def test (ctx):
	user = bot.get_user(ctx.message.author.id)
	message = await user.send(f"nyaa! have you finised your task?")
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

def update_restart(): # restart update loop
	global update_task
	if update_task != None:
		update_task.cancel()
	update_task = bot.loop.create_task(update())

@bot.command()
async def add(ctx, *args): # add activity command, argument time of day in HH:MM and name of the activity
	# users id
	id = ctx.message.author.id

	master = None
	for i in masters:
		if i["id"] == id:
			master = i
			break
	
	# if user isn't a master, create a new master from a template and assign users id
	if master == None:
		master = deepcopy(master_template)
		master["id"] = id
		masters.append(master)
		print(f"created new master with id {id}")

	# add a new activity and save
	add_activity(ctx, args, master)
	data_save()
	update_restart()

	await master_add(master, ctx)

@bot.command(aliases=["list", "activities", "tasks"])
async def _list(ctx):
	master = get_master(ctx.message.author.id)
	activities = []
	for i in master["activities"]:
		d = time.gmtime (i["time"])
		activities.append("{} {}".format(time.strftime("%H:%M", d), i["name"]))
	await master_list(master, ctx, '\n'.join(activities))

@bot.command()
async def remove(ctx, index):
	master = get_master(ctx.messages.author.id)
	if master["index"] >= index:
		master["index"] -= 1
	master["activities"].remove(index)

@atexit.register
def exit_handler():
	print("stopping maid bot.")

def get_master(id):
	for i in masters:
		if i["id"] == id:
			return i
	return None

async def master_ask(master):
	message = await bot.get_user(master["id"]).send(f"nyaa! have you finised your task?")
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

async def master_congratulate(master):
	await bot.get_user(master["id"]).send(f"nyaa! 👏 congrats!")

async def master_add(master, ctx):
	await ctx.send(f"nyaa! task added to your scheduele master!")

async def master_list(master, ctx, text):
	await ctx.send("nyaa! here is a list of all your tasks master!\n```{}```".format(text))

async def master_remove(master, ctx, text):
	await ctx.send("nyaa! i removed the task vrom your tasks!")

def add_activity(ctx, args, master):
	# create a new activity from a template
	new_activity = deepcopy(activity_template)

	new_activity["time"] = time_to_seconds(args[0])
	new_activity["name"] = " ".join(args[1:])

	# append activity to the master activities array
	master["activities"].append(new_activity)
	print (f"added new activity for master {master['id']} {new_activity} \n{masters}")

def time_to_seconds(time_string):
	h, m = time_string.split(":")
	return int(h) * 3600 + int(h) * 60

def data_save():
	save_data = {"date":date.strftime("%Y/%m/%d"), "masters":masters}

	with open(jsonfile, 'w') as fp:
		json.dump(save_data, fp)
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