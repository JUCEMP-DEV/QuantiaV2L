import { defineStore } from "pinia";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    accessProfile: "",
    accessToken: "",
    tokenType: "bearer",
  }),

  actions: {
    setUser(user) {
      this.user = user;
    },

    setAccessProfile(profile) {
      this.accessProfile = profile;
    },

    setAccessToken(accessToken, tokenType = "bearer") {
      this.accessToken = String(accessToken || "").trim();
      this.tokenType = String(tokenType || "bearer").trim().toLowerCase() || "bearer";
    },

    setSession({ user, accessToken = "", tokenType = "bearer" } = {}) {
      this.user = user || null;
      this.setAccessToken(accessToken, tokenType);
    },

    logout() {
      this.user = null;
      this.accessProfile = "";
      this.accessToken = "";
      this.tokenType = "bearer";
    },
  },
});
