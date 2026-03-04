import json
import random

import discord
from discord import app_commands
from discord.ext import commands

from database import db

DEFAULT_EDGE_CHANCE = 0.002
DEFAULT_EDGE_MESSAGE = '🪙 Ребро! Невероятно редкий исход.'
PLUGIN_SLUG = 'coin-flip'
PERIOD_OPTIONS = {
    '1d': ("AND created_at >= NOW() - INTERVAL '1 day'", '1 день'),
    '7d': ("AND created_at >= NOW() - INTERVAL '7 days'", '7 дней'),
    '30d': ("AND created_at >= NOW() - INTERVAL '30 days'", '30 дней'),
    'all': ('', 'всё время'),
}
ASCII_FLIPS = {
    'eagle': r'''
        .-=========-.
      .'   _  _    '.
     /   _( )( )_    \
    |   /  /\ /\ \    |
    |  |  /  V  \ |   |
    |  |  \_/\_/ |    |
     \  \   /\   /   /
      '. '.__.__.' .'
        '-._____.-'
'''.strip('\n'),
    'tails': r'''
        .-=========-.
      .'    ____   '.
     /    .'-..-'.   \
    |    /  /__\  \   |
    |    |  \__/  |   |
    |    \  .--.  /   |
     \    '.___.'    /
      '.           .'
        '-._____.-'
'''.strip('\n'),
    'edge': r'''
          __
       .-'  '-.
      /  .--.  \
      | |    | |
      | |    | |
      | |____| |
      \  '--'  /
       '-.__.-'
'''.strip('\n'),
}


class CoinFlip(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _as_settings(value):
        if isinstance(value, dict):
            return value
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        try:
            return dict(value)
        except Exception:
            return {}

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

        settings = self._as_settings(row['settings_json'] if row else None)

        try:
            edge_chance = float(settings.get('edge_chance', DEFAULT_EDGE_CHANCE))
        except (TypeError, ValueError):
            edge_chance = DEFAULT_EDGE_CHANCE

        edge_chance = min(max(edge_chance, 0.0), 1.0)
        edge_message = str(settings.get('edge_message', DEFAULT_EDGE_MESSAGE) or DEFAULT_EDGE_MESSAGE)

        return edge_chance, edge_message

    async def _build_stats_text(self, guild_id: int | None, period: str):
        if not guild_id:
            return 'Команда статистики доступна только на сервере.'

        await self._ensure_stats_table()
        key = str(period or 'all').strip().lower()
        where_clause, label = PERIOD_OPTIONS.get(key, PERIOD_OPTIONS['all'])
        total = await db.fetchval(
            f'''
            SELECT COUNT(*)
            FROM coin_flip_stats
            WHERE server_id = $1
            {where_clause}
            ''',
            guild_id,
        ) or 0
        eagle = await db.fetchval(
            f'''
            SELECT COUNT(*)
            FROM coin_flip_stats
            WHERE server_id = $1
              AND result = 'eagle'
              {where_clause}
            ''',
            guild_id,
        ) or 0
        tails = await db.fetchval(
            f'''
            SELECT COUNT(*)
            FROM coin_flip_stats
            WHERE server_id = $1
              AND result = 'tails'
              {where_clause}
            ''',
            guild_id,
        ) or 0
        edge = await db.fetchval(
            f'''
            SELECT COUNT(*)
            FROM coin_flip_stats
            WHERE server_id = $1
              AND result = 'edge'
              {where_clause}
            ''',
            guild_id,
        ) or 0

        if not total:
            return f'Статистика /coin за период "{label}" пока пустая.'

        def pct(value: int) -> str:
            return f'{(value / total) * 100:.1f}%'

        return (
            'Статистика /coin по всему серверу\n'
            f'Период: **{label}**\n'
            f'Всего: **{int(total)}**\n'
            f'🦅 Орел: **{int(eagle)}** ({pct(int(eagle))})\n'
            f'🪶 Решка: **{int(tails)}** ({pct(int(tails))})\n'
            f'🪙 Ребро: **{int(edge)}** ({pct(int(edge))})'
        )

    @app_commands.command(name='coin', description='Подбросить монетку: орел, решка или редкое ребро')
    @app_commands.describe(info='Показать статистику /coin вместо броска', period='Период статистики: 1d/7d/30d/all')
    @app_commands.choices(
        period=[
            app_commands.Choice(name='1 день', value='1d'),
            app_commands.Choice(name='7 дней', value='7d'),
            app_commands.Choice(name='30 дней', value='30d'),
            app_commands.Choice(name='Всё время', value='all'),
        ]
    )
    async def coin(self, interaction: discord.Interaction, info: bool = False, period: app_commands.Choice[str] | None = None):
        if info:
            selected_period = period.value if period else 'all'
            text = await self._build_stats_text(interaction.guild_id, selected_period)
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
        art = ASCII_FLIPS.get(result_key, '').strip()
        message = f'```{art}```\n{result}' if art else result
        await interaction.response.send_message(message, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinFlip(bot))


async def teardown(bot: commands.Bot):
    await bot.remove_cog('CoinFlip')
