# ISACbot


An example of a telegram bot that allows you to check employee attendance on Mondays.

> Created as a hobby project to simplify an annoying working task and provided "as is" without any warranty of any kind.

🤖 This bot allows you to:
- 📆 create and receive a poll about employee attendance on Mondays;
- 📧 send the results of a poll to the mailbox;
- 📝 register the user’s name and email;
- 🔒 participate in blocking/unblocking the roadmap (a work file filled out according to the activities of the department).


Can demonstrate some **HOW TO's**:
- use **aiogram** (long poolling technique) in combination with other modules;
- use **aiosqlite** as a simple sqlalchemy database storage;
- use **APScheduler** for job scheduling;
- use **GNU gettext** translation to achieve internationalization (**i18n**);
- use **SMTP** to transfer poll result data.


# Usage


## Linux/MacOS


As a first step, you should create your own bot and get a `BOT_TOKEN` from `@BotFather` in [telegram](https://telegram.org).

Then clone repository:
```bash
git clone https://github.com/pan-vlados/isacbot.git && cd isacbot
```
Create and fill in environment variables in [.env.prd](src/isacbot/config/.env.prd) file (use your favorite editor instead of `vi` 🤓):
```bash
cat src/isacbot/config/.env.dev > src/isacbot/config/.env.prd
vi !$
```
Compile language [translations](/src/isacbot/locales/) (supports 🇷🇺/🇺🇸 for users):
```bash
make i18n-compile
```
Run and enjoy 🥳:
```bash
make run
```

## Windows


*I believe in you!* 💪


## LICENSE
> MIT