import discord, atexit, time, json, asyncio
from discord.ext import commands
from datetime import datetime
from copy import deepcopy

token = "NDk0NTU5MDU3MTUyMzExMjk2.XntWMA.tdBff92dd0O5I-4mMR_3MxJw69A"
prefix = "."

bot = commands.Bot(command_prefix=prefix)

masters = []
master_template = {"id":0, "activities":[], "index":0}
activity_template = {"time":0, "name":""}

@bot.event
async def on_ready():
	# load all masters and their activities from json
	await bot.change_presence(activity=discord.Game("with copy.deepcopy()"))
	masters_load()
	print("maid bot is ready.")
	print(masters)

""" async def update():
	await bot.wait_until_ready()

	alarms = []
	while not bot.is_closed():
		t = datetime.now()
		delta = datetime.now()
		for master in masters:
			master_delta = master["activities"][master["index"]]["time"] - t
			if master_delta < delta:
				if master_delta <= 0:
					alarms.append(master)
				else:
					delta = master_delta

		for alarm in alarms:
			user = bot.get_user(alarm["id"])
			message = await user.send(f"nyaa! have you finised your task?")
			await message.add_reaction("✅")
			await message.add_reaction("⏰")
			reaction = await bot.wait_for_reaction(message=message)
			if reaction.emoji == "✅":
				alarms["index"] += 1

		await asyncio.sleep(delta) """

@bot.command()
async def bully(ctx):
	users = []
	for i in masters:
		users.append("<@{}>".format(i["id"]))
	await ctx.send("nyaa!! {} 😿 help me pls!!!".format(" ".join(users)))

@bot.command()
async def test (ctx):
	user = bot.get_user(ctx.message.author.id)
	message = await user.send(f"nyaa! have you finised your task?")
	await message.add_reaction("✅")
	await message.add_reaction("⏰")

@bot.event
async def on_reaction_add(reaction, user):
	if reaction.count > 1:
		await bot.get_user(204981328305848330).send(reaction.emoji)

# add activity command
@bot.command()
async def add(ctx, *args): # argument time of day in HH:MM and name of the activity
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
	masters_save()

@atexit.register
def exit_handler():
	print("stopping maid bot.")

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

def masters_save():
	with open('masters.json', 'w') as fp:
		json.dump(masters, fp)
		print("saved masters to json")

def masters_load():
	with open('masters.json') as json_file:
		jsondata = json.load(json_file)

		for i in jsondata:
			masters.append(i)
			print("loaded masters from json")

#bot.loop.create_task(update())
bot.run(token)