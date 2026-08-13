Placez ici `selfsigned.crt` et `selfsigned.key` (certificat auto-signe genere pour le LAN).

Generation rapide :
openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout selfsigned.key -out selfsigned.crt \
  -subj "/CN=sentinel-ops.local"
