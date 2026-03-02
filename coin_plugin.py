import random

import discord
from discord import app_commands
from discord.ext import commands


EDGE_CHANCE = 1 / 500


class CoinFlip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='coin', description='Подбросить монетку: орел, решка или редкое ребро')
    async def coin(self, interaction: discord.Interaction):
        roll = random.random()
        if roll < EDGE_CHANCE:
            result = '🪙 Ребро! Невероятно редкий исход.'
        elif random.choice([True, False]):
            result = '🦅 Орел'
        else:
            result = '🪶 Решка'

        await interaction.response.send_message(result)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinFlip(bot))


async def teardown(bot: commands.Bot):
    await bot.remove_cog('CoinFlip')
