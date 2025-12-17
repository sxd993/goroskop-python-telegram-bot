module.exports = {
  apps: [
    {
      name: "goroskop-bot-prod",
      cwd: __dirname,
      script: "scripts/run_prod.sh",
      interpreter: "bash",
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
      watch: false,
    },
  ],
};
