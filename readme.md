# Invoice Automation Bot

## Development
1. ```python3 -m venv .venv``` creates a virtual env named .venv
2. ```source .venv/bin/activate``` activates venv
3. ```pip install -r requirements.txt``` installs deps
4. ```uvicorn app2:app --reload --port 8080``` starts the app on port 8080. 8000 already taken.

## Production Environment Setups
1. ```python3 -m venv .venv``` creates a virtual env named .venv
2. ```source .venv/bin/activate``` activates venv
3. ```pip install -r requirements.txt``` installs deps
4. Create Gunicorn service ```sudo nano /etc/systemd/system/invoice_automation.service``` \
    **Update content to this**
    ```
    [Unit]
    Description=Gunicorn instance for FastAPI invoice_automation
    After=network.target

    [Service]
    User=ubuntu
    Group=www-data
    WorkingDirectory=/home/ubuntu/invoice_automation
    Environment="PATH=/home/ubuntu/invoice_automation/.venv/bin"
    ExecStart=/home/ubuntu/invoice_automation/.venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app2>

    [Install]
    WantedBy=multi-user.target
    ```
5. Execute these commands
    ```
    sudo systemctl daemon-reload
    sudo systemctl enable invoice_automation
    sudo systemctl start invoice_automation
    sudo systemctl status invoice_automation
    ```
6. Configure Nginx as Reverse Proxy
    ```
    sudo nano /etc/nginx/sites-available/invoice_automation
    ```
    Update Content
    ```
    server {
        server_name invoice-automation.chatdnas.com;

        location / {
                    proxy_pass http://127.0.0.1:8080;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```
7. Enable Nginx site
    ```
    sudo ln -s /etc/nginx/sites-available/invoice_automation /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx
    ```
8. Enabled HTTPS
    ```bash
    sudo apt install certbot python3-certbot-nginx -y
    sudo certbot --nginx -d invoice_automation.chatdnas.com # this takes care of auto renewal
    ```