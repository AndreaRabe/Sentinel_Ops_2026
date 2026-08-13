/**
 * Decodage (non verifie) du payload d'un JWT access token, pour lecture cote
 * UI uniquement (role, permissions). Le serveur reste seul juge de la
 * validite/expiration reelle du token.
 */
interface AccessTokenPayload {
  sub: string;
  role: string;
  perms: string[];
  exp: number;
}

export function decodeAccessToken(token: string): AccessTokenPayload {
  const payload = token.split(".")[1];
  const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(json) as AccessTokenPayload;
}
