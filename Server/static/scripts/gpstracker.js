
var map = '';
var markersArray = [];


window.onload = function(){
	initMap();
	getGPSData();
};


function initMap() {
    var centepoint = {lat: 50, lng: 0};
	
    map = new google.maps.Map(document.getElementById('map'), {
      zoom: 4,
      center: centepoint
    });
	
	
  }
  
function clearMapAndGetNewPos()
{
	clearMarkers();
	getGPSData();

}



function getGPSData() {
	var xmlhttp = new XMLHttpRequest();
	var URLbase = "http://192.168.4.70:8080/gpstracker/position/"
	var client = document.getElementById('client').value;
	var url = URLbase + client + "/latest";

	xmlhttp.onreadystatechange = function() {
		if (this.readyState == 4 && this.status == 200) {
			var myArr = JSON.parse(this.responseText);
			parseResponseJson(myArr);
		}
	};
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}


function parseResponseJson(jresponse) {
	if (jresponse.status == 'ok') {
		for (var i = 0; i < jresponse.data.gpsdatalist.length; i++) {
			var point = new google.maps.LatLng(
				parseFloat(jresponse.data.gpsdatalist[i].lat),
				parseFloat(jresponse.data.gpsdatalist[i].lng));
				
			var marker = new google.maps.Marker({
			  position: point,
			  map : map
			  });
			 markersArray.push(marker);
		}	
	}	
}

function clearMarkers() {
	while(markersArray.length) { markersArray.pop().setMap(null); }
}



<script async defer
src="https://maps.googleapis.com/maps/api/js?key=AIzaSyCbh6_Jhpzj13qeM6Ujw_vjJZOK85o3SsI&callback=initMap">
</script>
