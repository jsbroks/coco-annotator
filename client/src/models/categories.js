import axios from "axios";

const baseURL = "/api/category/";

export default {
  allData(params) {
    return axios.get(baseURL + "data", {
      params: {
        ...params
      }
    });
  },
  create(create) {
    return axios.post(baseURL, { ...create });
  }
};
