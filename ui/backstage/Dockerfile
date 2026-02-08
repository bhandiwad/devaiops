FROM nginx:1.27-alpine

COPY ui/backstage/packages/app/dist /usr/share/nginx/html
COPY ui/backstage/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
