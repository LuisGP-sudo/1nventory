# ---------- Stage 1 : build / validation ----------
FROM nginx:alpine AS build
COPY nginx.conf /etc/nginx/nginx.conf
COPY public/ /usr/share/nginx/html/
# Fait échouer le build si la configuration nginx est invalide
RUN nginx -t

# ---------- Stage 2 : image finale ----------
FROM nginx:alpine
COPY --from=build /etc/nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /usr/share/nginx/html /usr/share/nginx/html

# Utilisateur non-root (déjà présent dans l'image nginx:alpine)
USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/health || exit 1

# On neutralise l'entrypoint officiel (scripts conçus pour root)
ENTRYPOINT []
CMD ["nginx", "-g", "daemon off;"]
