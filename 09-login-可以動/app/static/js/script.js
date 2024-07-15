// 初始化地圖
async function initMap() {
    // 獲取用戶當前位置
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
        // navigator.geolocation 是 JavaScript 中內建的 API，它允許您從用戶的瀏覽器中獲取當前的地理位置
        //.getCurrentPosition 是 HTML5 Geolocation API 的一個內建方法。這個方法用於從用戶的瀏覽器獲取當前的地理位置信息，
        // 前提是用戶必須授予網站訪問位置的權限。

        // 這裡的 position 餐廳的情景：
        //點餐：你告訴服務員你想要什麼。這就像你通過 navigator.geolocation.getCurrentPosition() 命令告訴瀏覽器："請給我當前的地理位置信息。"
        //等待食物：服務員去廚房（地理位置信息服務）處理你的訂單，而你繼續聊天或做其他事情，不需要一直站在櫃檯前等著。這就是所謂的異步操作——你不需要停下其他活動來等待回應。
        //上菜：當食物（位置數據）準備好後，服務員會把它送到你的桌上。在網頁程序中，這一步對應於位置數據一旦可用，你提供給 getCurrentPosition() 的回調函數(position)就會被調用，並且給你要的緯度跟經度。
            var userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };

            console.log("User location:", userLocation);

            // 創建地圖對象
            var map = new google.maps.Map(document.getElementById('map'), {
        //new google.maps.Map(...)：這一行創建一個新的地圖實例。這是 Google Maps API 中的一個構造函數，用來生成新的地圖。
        //document 對象提供了許多方法和屬性，允許開發者訪問和操作網頁的內容。ex:getElementById
                center: userLocation,
                zoom: 14
            });

            // 在地圖上添加標記
            var userMarker = new google.maps.Marker({
            //是 Google Maps JavaScript API 的一部分，提供的一個用於在地圖上創建和管理標記（marker）的構造函數。
                position: userLocation,
                map: map,
                title: 'You are here'
            });

            // 使用 Google Places API 查找附近的健身房
            // Google Maps JavaScript API 的 PlacesService 來搜索附近的地點（在這個例子中是健身房）。
            var service = new google.maps.places.PlacesService(map);

            service.nearbySearch({ //service.nearbySearch() 是 Google Maps Places API 提供的一個內建方法
            //這個方法是用來在 Google 地圖上尋找指定位置附近的特定類型的地點，例如餐館、商店、健身房等。
                location: userLocation,
                radius: 15000,  // 設置搜索範圍，單位為米
                type: ['gym']  // 搜索類型設置為健身房
            }, function(results, status) {
                if (status === google.maps.places.PlacesServiceStatus.OK) {
                //status: 表示搜索的狀態，如果狀態為 OK，則表示搜索成功並且至少找到一個結果。
                    for (var i = 0; i < results.length; i++) {
// results 是一個數組，包含了所有符合搜索條件的地點。每個元素都是一個對象，描述了一個地點的詳細信息，如地點的名稱、地理位置、評分等。
// 每個地點對象包含 geometry 屬性，其中的 location 屬性表示該地點的具體經緯度坐標。
                        var place = results[i];
                        var marker = new google.maps.Marker({
// 使用 Google Maps JavaScript API 中提供的 Marker API 創建的一個標記（marker）。
// Marker API 允許開發者在地圖上放置自定義的標記點，以此來表示特定的地理位置。
// 如果 status 為 OK，則進入 if 語句塊執行更深入的處理。
// 遍歷 results 數組中的每一個地點：只要有找到一個健身房，就給一個 Marker
// 從每個地點的 geometry.location 獲取地理位置。
// 為每個地點創建一個新的標記（Marker），並將其添加到地圖上。這些標記使用地點的名稱作為標題，當用戶點擊或懸停時可以看到。
                            position: place.geometry.location,
                            map: map,
                            title: place.name
                        });



                        var infoWindow = new google.maps.InfoWindow();
                        google.maps.event.addListener(marker, 'click', (function(marker, place) {
                            return function() {
                                infoWindow.setContent(place.name);
                                infoWindow.open(map, marker);
                            }
                        })(marker, place));
                    }
                } else {
                    console.error('PlacesService status: ' + status);
                }
            });
        }, function(error) {
            console.error('Error occurred. Error code: ' + error.code);
            var map = new google.maps.Map(document.getElementById('map'), {
                center: {lat: 43.4142989, lng: -124.2301242},
                zoom: 4
            });
        });
    } else {
        var map = new google.maps.Map(document.getElementById('map'), {
            center: {lat: 43.4142989, lng: -124.2301242},
            zoom: 4
        });
    }
}
