# HUMAN Extension Example: Coin Flip

Пример внешнего плагина для HUMAN Bot.

Плагин добавляет slash-команду `/coin`:
- `Орел`
- `Решка`
- очень маленький шанс на `Ребро` (по умолчанию 1/500)

## 1) Состав репозитория

- `plugin.json` - манифест для установщика HUMAN Bot.
- `coin_plugin.py` - реализация плагина.

## 2) Манифест

```json
{
  "slug": "coin-flip",
  "name": "Coin Flip",
  "version": "1.0.0",
  "description": "Slash command /coin: орел или решка с очень маленьким шансом на ребро.",
  "entrypoint": "coin_plugin.py",
  "min_bot_version": "1.2.0"
}
```

Обязательные поля:
- `slug`
- `name`
- `version`
- `entrypoint`

## 3) Как выпустить релиз на GitHub

1. Закоммитьте код:
```bash
git add .
git commit -m "feat: initial coin plugin"
git push origin main
```

2. Создайте архив для релиза (важно: внутри архива должны быть `plugin.json` и `coin_plugin.py`):

Linux/macOS:
```bash
zip -r coin-flip-v1.0.0.zip plugin.json coin_plugin.py
```

Windows PowerShell:
```powershell
Compress-Archive -Path .\plugin.json, .\coin_plugin.py -DestinationPath .\coin-flip-v1.0.0.zip -Force
```

3. На GitHub откройте `Releases -> Draft a new release`.
4. Укажите tag, например `v1.0.0`.
5. Прикрепите архив `coin-flip-v1.0.0.zip` как asset.
6. Опубликуйте релиз.

## 4) Установка через панель HUMAN Bot

1. Скопируйте прямой URL к release asset.
2. В панели бота откройте раздел `Плагины`.
3. Вставьте URL в поле `Release Asset URL`.
4. Нажмите `Установить плагин`.
5. После `Enable` команда `/coin` появится на сервере.

## 5) Локальная проверка

Быстрая проверка синтаксиса:

```bash
python -m compileall coin_plugin.py
```

## 6) Как писать свои расширения

Минимальный шаблон:

```python
from discord.ext import commands

class MyPlugin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(MyPlugin(bot))

async def teardown(bot):
    await bot.remove_cog('MyPlugin')
```

Рекомендации:
- всегда реализуйте `teardown`,
- избегайте блокирующих операций в обработчиках команд,
- версионируйте изменения (`version` в `plugin.json`),
- публикуйте changelog в каждом GitHub release.
