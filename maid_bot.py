import discord
from discord.ext import commands

token = "NDk0NTU5MDU3MTUyMzExMjk2.XntWMA.tdBff92dd0O5I-4mMR_3MxJw69A"
client = commands.Bot(command_prefix=".")

@client.event
async def on_ready():
    print("maid bot is ready.")

client.run(token)