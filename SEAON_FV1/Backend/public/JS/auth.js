/* AUTHENTICATION
   Login state is kept in browser storage and the server validates the JWT
   on every protected API request.
*/
window.Auth={
  isAuthenticated(){return Boolean(localStorage.getItem("seaon_access_token"));},
  user(){try{return JSON.parse(localStorage.getItem("seaon_user")||"null")}catch{return null}},
  async login(email,password){
    const data=await API.auth.login(email,password);
    localStorage.setItem("seaon_access_token",data.access);
    localStorage.setItem("seaon_refresh_token",data.refresh);
    localStorage.setItem("seaon_user",JSON.stringify(data.user));
    return data.user;
  },
  async logout(){
    try{await API.auth.logout()}catch{}
    localStorage.removeItem("seaon_access_token");
    localStorage.removeItem("seaon_refresh_token");
    localStorage.removeItem("seaon_user");
    location.href="/app/login.html";
  }
};
