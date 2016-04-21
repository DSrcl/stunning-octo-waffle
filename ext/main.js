console.log(chrome);
chrome.webNavigation.onCommitted.addListener(function(data) {
	var url = data.url;
	console.log(url);
	var xhr = new XMLHttpRequest();
	if (url != "about:blank" &&
		url.indexOf("http://localhost:5000") === -1) {
		xhr.open("GET", "http://localhost:5000/links?user=tom&url="+url, true);
		xhr.send();
	}
});

