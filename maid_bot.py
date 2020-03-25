import discord, atexit, time, copy, json, asyncio
from discord.ext import commands
from datetime import datetime

token = "NDk0NTU5MDU3MTUyMzExMjk2.XntWMA.tdBff92dd0O5I-4mMR_3MxJw69A"
prefix = "."

bot = commands.Bot(command_prefix=prefix)

masters = []
master_template = {"id":0, "activities":[], "index":0}
activity_template = {"time":0, "name":""}

@bot.event
async def on_ready():
	print("maid bot is ready.")
	masters_load()
	print (masters)

@bot.command()
async def add(ctx, *args):
	id = ctx.message.author.id

	for master in masters:
		if master["id"] == id:
			add_activity(ctx, args, master)
			masters_save()
			return
	
	print(f"created new master with id {id}")
	new_master = copy.deepcopy(master_template)
	new_master["id"] = id
	add_activity(ctx, args, new_master)
	masters.append(new_master)
	masters_save()

@atexit.register
def exit_handler():
	print("\nstopping maid bot.")

def add_activity(ctx, args, master):
	new_activity = copy.deepcopy(activity_template)

	text = ""
	for i in args[1:]:
		text += str(i) + " "
		
	new_activity["time"] = time_to_seconds(args[0])
	new_activity["name"] = text[:len(text)-1]

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
			new_master = copy.deepcopy(master_template)
			new_master["id"] = i["id"]

			for j in i["activities"]:
				new_activity = copy.deepcopy(activity_template)
				new_activity["time"] = j["time"]
				new_activity["name"] = j["name"]
				new_master["activities"].append(new_activity)

			masters.append(new_master)
			print("loaded masters from json")

async def update():
	alarms = []
	while not bot.is_closed():
		t = datetime.now()
		delta = datetime.now()
		for master in masters:
			master_delta = master["activities"][master["index"]]["time"] - t
			if master_delta < delta:
				if master_delta < 0:
					alarms.append(master)
				else:
					delta = master_delta

		for alarm in alarms:
			user = bot.get_user(alarm["id"])
			await message = user.send(f"nyaa! have you finised your task?")

		await asyncio.sleep(delta)



bot.run(token)