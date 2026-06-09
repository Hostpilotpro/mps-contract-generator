// Simple in-memory auth store — works everywhere (no cookies, no localStorage)
let _token: string | null = null;
let _user: { username: string; role: string } | null = null;

export const authStore = {
  getToken: ()  => _token,
  getUser:  ()  => _user,
  isLoggedIn: () => !!_token,
  login: (token: string, user: { username: string; role: string }) => {
    _token = token;
    _user  = user;
  },
  logout: () => {
    _token = null;
    _user  = null;
  },
};
