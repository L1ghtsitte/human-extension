import random

import discord
from discord import app_commands
from discord.ext import commands

from database import db

DEFAULT_EDGE_CHANCE = 0.002
DEFAULT_EDGE_MESSAGE = '🪙 Ребро! Невероятно редкий исход.'
PLUGIN_SLUG = 'coin-flip'
ASCII_FLIPS = {
    'eagle': r'''
   .------.
 .'  /\   '.
/   /  \    \
|  | () |   |
\   \__/   /
 '.      .'
   '----'
'''.strip('\n'),
    'tails': r'''
   .------.
 .'  __   '.
/   /__\    \
|   \__/    |
\    /\    /
 '.      .'
   '----'
'''.strip('\n'),
    'edge': r'''
    _____
  /  ___ \
 |  |   | |
 |  |   | |
 |  |___| |
  \_____ /
'''.strip('\n'),
}


class CoinFlip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ensure_stats_table(self):
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS coin_flip_stats (
                id BIGSERIAL PRIMARY KEY,
                server_id BIGINT,
                user_id BIGINT,
                result VARCHAR(16) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        await db.execute('CREATE INDEX IF NOT EXISTS idx_coin_flip_stats_server_created ON coin_flip_stats(server_id, created_at DESC)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_coin_flip_stats_server_result ON coin_flip_stats(server_id, result)')

    async def _load_settings(self, guild_id: int | None):
        if not guild_id:
            return DEFAULT_EDGE_CHANCE, DEFAULT_EDGE_MESSAGE

        row = await db.fetchrow(
            '''
            SELECT settings_json
            FROM plugin_settings
            WHERE server_id = $1 AND plugin_slug = $2
            ''',
            guild_id,
            PLUGIN_SLUG,
        )

        settings = dict(row['settings_json']) if row and row['settings_json'] else {}

        try:
            edge_chance = float(settings.get('edge_chance', DEFAULT_EDGE_CHANCE))
        except (TypeError, ValueError):
            edge_chance = DEFAULT_EDGE_CHANCE

        edge_chance = min(max(edge_chance, 0.0), 1.0)
        edge_message = str(settings.get('edge_message', DEFAULT_EDGE_MESSAGE) or DEFAULT_EDGE_MESSAGE)

        return edge_chance, edge_message

    async def _build_stats_text(self, guild_id: int | None):
        if not guild_id:
            return 'Команда статистики доступна только на сервере.'

        await self._ensure_stats_table()
        total = await db.fetchval('SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1', guild_id) or 0
        eagle = await db.fetchval("SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1 AND result = 'eagle'", guild_id) or 0
        tails = await db.fetchval("SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1 AND result = 'tails'", guild_id) or 0
        edge = await db.fetchval("SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1 AND result = 'edge'", guild_id) or 0
        week_total = await db.fetchval(
            '''
            SELECT COUNT(*)
            FROM coin_flip_stats
            WHERE server_id = $1
              AND created_at >= NOW() - INTERVAL '7 days'
            ''',
            guild_id,
        ) or 0

        if not total:
            return 'Статистика /coin пока пустая.'

        def pct(value: int) -> str:
            return f'{(value / total) * 100:.1f}%'

        return (
            'Статистика /coin по всему серверу\n'
            f'Всего: **{int(total)}**\n'
            f'За 7 дней: **{int(week_total)}**\n'
            f'🦅 Орел: **{int(eagle)}** ({pct(int(eagle))})\n'
            f'🪶 Решка: **{int(tails)}** ({pct(int(tails))})\n'
            f'🪙 Ребро: **{int(edge)}** ({pct(int(edge))})'
        )

    @app_commands.command(name='coin', description='Подбросить монетку: орел, решка или редкое ребро')
    @app_commands.describe(info='Показать статистику /coin вместо броска')
    async def coin(self, interaction: discord.Interaction, info: bool = False):
        if info:
            text = await self._build_stats_text(interaction.guild_id)
            await interaction.response.send_message(text, ephemeral=False)
            return

        edge_chance, edge_message = await self._load_settings(interaction.guild_id)
        roll = random.random()

        if roll < edge_chance:
            result_key = 'edge'
            result = edge_message
        elif random.choice([True, False]):
            result_key = 'eagle'
            result = '🦅 Орел'
        else:
            result_key = 'tails'
            result = '🪶 Решка'

        await self._ensure_stats_table()
        await db.execute(
            '''
            INSERT INTO coin_flip_stats (server_id, user_id, result)
            VALUES ($1, $2, $3)
            ''',
            interaction.guild_id,
            interaction.user.id if interaction.user else None,
            result_key,
        )
        total = await db.fetchval('SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1', interaction.guild_id) or 0
        eagle = await db.fetchval("SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1 AND result = 'eagle'", interaction.guild_id) or 0
        tails = await db.fetchval("SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1 AND result = 'tails'", interaction.guild_id) or 0
        edge = await db.fetchval("SELECT COUNT(*) FROM coin_flip_stats WHERE server_id = $1 AND result = 'edge'", interaction.guild_id) or 0
        art = ASCII_FLIPS.get(result_key, '').strip()
        stats_line = f'Статистика сервера: всего {int(total)} | орел {int(eagle)} | решка {int(tails)} | ребро {int(edge)}'
        message = f'```{art}```\n{result}\n{stats_line}' if art else f'{result}\n{stats_line}'
        await interaction.response.send_message(message, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinFlip(bot))


async def teardown(bot: commands.Bot):
    await bot.remove_cog('CoinFlip')
