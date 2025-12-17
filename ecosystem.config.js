module.exports = {
  apps: [
    {
      name: "goroskop-bot-prod",
      cwd: __dirname,
      script: "app.py",
      interpreter: "./.venv/bin/python",
      env: {
        ENV_FILE: ".env.prod",
        PYTHONUNBUFFERED: "1",
      },
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
      watch: false,
    },
  ],
};
