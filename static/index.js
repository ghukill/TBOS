var data = {a: "sup boss."}
var vm = new Vue({
    el: '#vm',
    data: data,
    delimiters: ['[[', ']]'],
    methods: {
        apiPing: function () {
            axios.get('http://localhost:5000/api/debug/ping')
                .then(response => {
                    const ping = response;
                    alert(response.data);
                })
                .catch(error => console.error(error));
        }
    }
})

