FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
