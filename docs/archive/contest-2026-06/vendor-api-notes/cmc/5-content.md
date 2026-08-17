Content
Endpoints for content data. This category includes 4 endpoints:

    /v1/content/latest - Content Latest
    /v1/content/posts/top - Content Top Posts
    /v1/content/posts/latest - Content Latest Posts
    /v1/content/posts/comments - Content Post Comments

Content Latest
GET
https://pro-api.coinmarketcap.com
/v1/content/latest

Returns a paginated list of content pulled from CMC News/Headlines and Alexandria articles.

This endpoint is available on the following API plans:

    Standard
    Professional
    Enterprise

Cache / Update frequency: Five Minutes Plan credit use: 0 credit
Content Latest › query Parameters
start
​integer · min: 1

Optionally offset the start (1-based index) of the paginated list of items to return.
Default: 1
limit
​integer · min: 1 · max: 200

Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size.
Default: 100
id
​string · pattern: ^\d+(?:,\d+)*$

Optionally pass a comma-separated list of CoinMarketCap cryptocurrency IDs. Example: "1,1027"
slug
​string · pattern: ^[0-9a-z-]+(?:,[0-9a…

Optionally pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-,]+(?…

Optionally pass a comma-separated list of cryptocurrency symbols. Example: "BTC,ETH". Optionally pass "id" or "slug" or "symbol" is required for this request.
news_type
​string · pattern: ^(news|community|ale…

Optionally specify a comma-separated list of supplemental data fields: news, community, or alexandria to filter news sources. Pass all or leave it blank to include all news types.
Default: all
content_type
​string · pattern: ^(audio|news|video|a…

Optionally specify a comma-separated list of supplemental data fields: news, video, or audio to filter news's content. Pass all or leave it blank to include all content types.
Default: all
category
​string

Optionally pass a comma-separated list of categories. Example: "GameFi,NFT".
language
​string · enum

Optionally pass a language code. Example: "en". If not specified the default value is "en".
Enum values:
en
zh
zh-tw
de
id
ja
ko
es
Default: en
Content Latest › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Content Latest › Responses

Successful
Content_Latest_-_Response_Model
​Model_1[] · required

Array of content objects.
​API_Status_Object · required

Standardized status object for API calls.
GET/v1/content/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/content/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "cover": "https://academy-public.coinmarketcap.com/optimized-uploads/0aec0502868046419ceace229f92601f.gif",
      "assets": [
        {
          "id": 1027,
          "name": "Ethereum",
          "symbol": "ETH",
          "slug": "ethereum"
        }
      ],
      "created_at": "2021-05-05T00:00:00Z",
      "released_at": "2021-05-05T00:00:00Z",
      "title": "Article Title",
      "subtitle": "Article Subtitle",
      "type": "alexandria",
      "source_name": "Connor Sephton",
      "source_url": "https://coinmarketcap.com/alexandria/article/coinmarketcap-news-august-9-u-s-comes-for-tornado-cash"
    }
  ],
  "status": {
    "timestamp": "2018-06-02T22:51:28.209Z",
    "error_code": 0,
    "error_message": "",
    "elapsed": 10,
    "credit_count": 1
  }
}
json
application/json
Content Post Comments
GET
https://pro-api.coinmarketcap.com
/v1/content/posts/comments

Returns comments of the CMC Community post.

This endpoint is available on the following API plans:

    Standard
    Professional
    Enterprise

Cache / Update frequency: Five Minutes Plan credit use: 0 credit
Content Post Comments › query Parameters
post_id
​string · pattern: ^\d*$ · required

Required post ID. Example: 325670123
Content Post Comments › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Content Post Comments › Responses

Successful
Content_Post_Comments_-_Response_Model
​Model_2[] · required

Array of content objects.
​API_Status_Object

Standardized status object for API calls.
GET/v1/content/posts/comments
curl --request GET \
  --url 'https://pro-api.coinmarketcap.com/v1/content/posts/comments?post_id=%3Cstring%3E' \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": [
    {
      "post_id": "317807035",
      "owner": {
        "nickname": "Amy",
        "avatar_url": "https://s3.coinmarketcap.com/static/img/portraits/61359449293ccc2c4bcf07c7.png"
      },
      "text_content": "Someone's working on it!!",
      "photos": [],
      "comment_count": "0",
      "like_count": "0",
      "post_time": "1662640110429",
      "language_code": "en"
    },
    {
      "post_id": "317807862",
      "owner": {
        "nickname": "Wanda",
        "avatar_url": "https://s3.coinmarketcap.com/static/img/portraits/6136cf1015b8f3308e283073.png"
      },
      "text_content": "yes sir!!",
      "photos": [],
      "comment_count": "0",
      "like_count": "0",
      "post_time": "1662635039889",
      "language_code": "en"
    }
  ],
  "status": {
    "timestamp": "2022-09-08T16:07:30.033Z",
    "error_code": 0,
    "error_message": "SUCCESS",
    "elapsed": 10,
    "credit_count": 0
  }
}
json
application/json
Content Latest Posts
GET
https://pro-api.coinmarketcap.com
/v1/content/posts/latest

Returns the latest crypto-related posts from the CMC Community.

This endpoint is available on the following API plans:

    Standard
    Professional
    Enterprise

Cache / Update frequency: Five Minutes Plan credit use: 0 credit
Content Latest Posts › query Parameters
id
​string · pattern: ^\d*$

Optional one cryptocurrency CoinMarketCap ID. Example: 1027
slug
​string · pattern: ^[0-9a-z-]*$

Alternatively pass one cryptocurrency slug. Example: "ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-]*$

Alternatively pass one cryptocurrency symbols. Example: "ETH"
last_score
​string

Optional. The score is given in the response for finding next batch posts. Example: 1662903634322
Content Latest Posts › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Content Latest Posts › Responses

Successful
Content_Latest_Posts_-_Response_Model
​Content_Top_Posts_-_Results · required

Cntent objects.
GET/v1/content/posts/latest
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/content/posts/latest \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "list": [
      {
        "post_id": "123456789",
        "comments_url": "{{baseUrl}}/v1/content/posts/comments?post_id=123456789",
        "owner": {
          "nickname": "CoinMarketCap",
          "avatar_url": "https://s3.coinmarketcap.com/static/img/portraits/621c22097aafe46422aa1161.png"
        },
        "text_content": "$ETH regardless of merging or not merging...",
        "photos": [
          "https://s3.coinmarketcap.com/static/img/portraits/621c22097aafe46422aa1161.png"
        ],
        "comment_count": "5",
        "like_count": "5",
        "post_time": "1662643031298",
        "currencies": [
          {
            "id": 1027,
            "symbol": "ETH",
            "slug": "ethereum"
          }
        ],
        "language_code": "en"
      },
      {
        "post_id": "123456790",
        "comments_url": "{{baseUrl}}/v1/content/posts/comments?post_id=123456790",
        "owner": {
          "nickname": "John",
          "avatar_url": "https://s3.coinmarketcap.com/static/img/portraits/61b9aaca1d79d0637758fdeb.png"
        },
        "text_content": "$ETH The success and the failure are almost...",
        "photos": [
          "https://s3.coinmarketcap.com/static/img/portraits/621c22097aafe46422aa1161.png"
        ],
        "comment_count": "6",
        "like_count": "60",
        "post_time": "1662612816768",
        "currencies": [
          {
            "id": 1027,
            "symbol": "ETH",
            "slug": "ethereum"
          }
        ],
        "repost_count": "0",
        "language_code": "en"
      }
    ],
    "last_score": "1662903634322"
  }
}
json
application/json
Content Top Posts
GET
https://pro-api.coinmarketcap.com
/v1/content/posts/top

Returns the top crypto-related posts from the CMC Community.

This endpoint is available on the following API plans:

    Standard
    Professional
    Enterprise

Cache / Update frequency: Five Minutes Plan credit use: 0 credit
Content Top Posts › query Parameters
id
​string · pattern: ^\d*$

Optional one cryptocurrency CoinMarketCap ID. Example: 1027
slug
​string · pattern: ^[0-9a-z-]*$

Alternatively pass one cryptocurrency slug. Example: "ethereum"
symbol
​string · pattern: ^[0-9A-Za-z$@\-]*$

Alternatively pass one cryptocurrency symbols. Example: "ETH"
last_score
​string

Optional. The score is given in the response for finding next batch of related posts. Example: 38507.8865
Content Top Posts › Headers
X-CMC_PRO_API_KEY
​string · required

Your CoinMarketCap Pro API key
Default: YOUR_API_KEY
Content Top Posts › Responses

Successful
Content_Top_Posts_-_Response_Model
​Content_Top_Posts_-_Results · required

Cntent objects.
​API_Status_Object

Standardized status object for API calls.
GET/v1/content/posts/top
curl --request GET \
  --url https://pro-api.coinmarketcap.com/v1/content/posts/top \
  --header 'X-CMC_PRO_API_KEY: YOUR_API_KEY'
Example Responses
{
  "data": {
    "list": [
      {
        "post_id": "123456789",
        "comments_url": "{{baseUrl}}/v1/content/posts/comments?post_id=123456789",
        "owner": {
          "nickname": "CoinMarketCap",
          "avatar_url": "https://s3.coinmarketcap.com/static/img/portraits/621c22097aafe46422aa1161.png"
        },
        "text_content": "$ETH regardless of merging or not merging...",
        "photos": [
          "https://s3.coinmarketcap.com/static/img/portraits/621c22097aafe46422aa1161.png"
        ],
        "comment_count": "5",
        "like_count": "5",
        "post_time": "1662643031298",
        "currencies": [
          {
            "id": 1027,
            "symbol": "ETH",
            "slug": "ethereum"
          }
        ],
        "language_code": "en"
      },
      {
        "post_id": "123456790",
        "comments_url": "{{baseUrl}}/v1/content/posts/comments?post_id=123456790",
        "owner": {
          "nickname": "John",
          "avatar_url": "https://s3.coinmarketcap.com/static/img/portraits/61b9aaca1d79d0637758fdeb.png"
        },
        "text_content": "$ETH The success and the failure are almost...",
        "photos": [
          "https://s3.coinmarketcap.com/static/img/portraits/621c22097aafe46422aa1161.png"
        ],
        "comment_count": "6",
        "like_count": "60",
        "post_time": "1662612816768",
        "currencies": [
          {
            "id": 1027,
            "symbol": "ETH",
            "slug": "ethereum"
          }
        ],
        "repost_count": "0",
        "language_code": "en"
      }
    ],
    "last_score": "38507.8865"
  },
  "status": {
    "timestamp": "2022-09-08T16:08:52.641Z",
    "error_code": 0,
    "error_message": "SUCCESS",
    "elapsed": 0,
    "credit_count": 0
  }
}
json
application/json
