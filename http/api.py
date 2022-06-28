from collections import defaultdict, OrderedDict

import requests
from urllib.parse import urlparse, urlsplit, parse_qs
import json
from user import User


def get_friends_response(token):
    return requests.get((f'https://api.vk.com/method/friends.get?&access_token={token}&v=5.131'))


def get_wall_post_response(token):
    return requests.get(f'https://api.vk.com/method/wall.get?count=100&access_token={token}&v=5.131')


def get_wall_post_likes_response(token, post_id):
    return requests.get(
        f'https://api.vk.com/method/likes.getList?type=post&item_id={post_id}&friends_only=1&extended=1&'
        f'access_token={token}&v=5.131')


def get_wall_post_comments_response(token, post_id):
    return requests.get(f'https://api.vk.com/method/wall.getComments?post_id={post_id}&extended=1&'
                        f'access_token={token}&v=5.131')


def main():
    url = (input('Введите ссылку: \n')).replace('#', '?')
    queries = parse_qs(urlsplit(url).query)
    token = queries['access_token'][0]
    posts = json.loads(get_wall_post_response(token).content)['response']['items']
    friends = json.loads(get_friends_response(token).content)['response']['items']
    users_by_id = {}
    statistic = defaultdict(lambda: defaultdict(int))
    i = -1
    for post in posts:
        i += 1
        post_id = post['id']
        print(f'progress: {i}/{len(posts)}')
        post_likes = json.loads(get_wall_post_likes_response(token, post_id).content)
        post_comments = json.loads(get_wall_post_comments_response(token, post_id).content)
        if 'response' in post_comments and 'profiles' in post_comments['response']:
            comment_profiles = post_comments['response']['profiles']
            for comment in comment_profiles:
                if comment['id'] not in friends:
                    continue
                if comment['id'] not in users_by_id:
                    users_by_id[comment['id']] = User(comment['first_name'], comment['last_name'])
                statistic[comment['id']]['comments'] += 1
        if 'response' in post_likes:
            likes_items = post_likes['response']['items']
            for like in likes_items:
                if like['id'] not in users_by_id:
                    users_by_id[like['id']] = User(like['first_name'], like['last_name'])
                statistic[like['id']]['likes'] += 1
    sorted_stat = dict(sorted(statistic.items(), key=lambda item: item[1]['likes'] + item[1]['comments'], reverse=True))
    print('Список друзей в порядке убывания лайков + комментов')
    for key in sorted_stat:
        print(f'{users_by_id[key]}: Likes {sorted_stat[key]["likes"]} + Comments {sorted_stat[key]["comments"]}')


if __name__ == '__main__':
    main()