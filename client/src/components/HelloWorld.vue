<template>
  <div class="hello">
    <h1>{{ msg }}</h1>
  </div>
</template>

<script>
import axios from "axios";

export default {
	name: "HelloWorld",
	props: {
		msg: {
			type: String,
			required: true
		}
	},
	created() {
		console.log("test");
		axios.get("/api/image").then(response => {
			console.log(response);
		});
	}
};
</script>

<style scoped>
h3 {
	margin: 40px 0 0;
}
ul {
	list-style-type: none;
	padding: 0;
}
li {
	display: inline-block;
	margin: 0 10px;
}
a {
	color: #42b983;
}
</style>
