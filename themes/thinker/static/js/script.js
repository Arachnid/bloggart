// My Scripts
jQuery.noConflict();
jQuery(document).ready(function() {
    
});

//FeedApi
google.setOnLoadCallback(onLoadOfFeedApi);
function onLoadOfFeedApi() {
  //var feed1 = new google.feeds.push.Feed("http://johnturner.posterous.com/rss.xml");
  //feed1.includeHistoricalEntries(2);
  //feed1.subscribe(renderFeedsPosterous)
  var feed2 = new google.feeds.push.Feed("http://feeds.delicious.com/v2/rss/johnnytee/");
  feed2.includeHistoricalEntries(3);
  feed2.subscribe(renderFeedsDelicious)
  var feed3 = new    google.feeds.push.Feed("http://www.google.com/reader/public/atom/user/08477895806911596398/state/com.google/broadcast");
  feed3.includeHistoricalEntries(3);
  feed3.subscribe(renderFeedsReader)

}

function renderFeedsPosterous(response) {
    renderFeeds(response,'update-posterous')
  }
function renderFeedsDelicious(response) {
    renderFeeds(response,'update-delicious')
  }
function renderFeedsReader(response) {
    renderFeeds(response,'update-reader')
  }
function renderFeeds(response,class) {
  var entries = response.feed.entries;
  for (var i = 0; i < entries.length; i++) {
    //console.log(entries[i])
    jQuery("#widget-realtime ul").prepend("<li class='"+class+"'><a href='"+entries[i].link+"'>"+entries[i].title+"</a></li>")
  }
}
