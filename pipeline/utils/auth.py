import requests
from django.conf import settings


def create_admin_user(uid, response, details, user, social, *args, **kwargs):
    # assume github-team backend, add <if backend.name == 'github-team'>
    # if other backend are implemented
    admin_team = settings.SOCIAL_AUTH_GITHUB_TEAM_ADMIN
    usr = response.get('login', '')
    if (usr != '' and admin_team != '' and user and not user.is_staff and
        not user.is_superuser):
        # check if github user belong to team
        org = 'askap-vast'
        header = {
            'Authorization': f"token {response.get('access_token', '')}"
        }
        url = (
            f'https://api.github.com/orgs/{org}/teams/{admin_team}'
            f'/memberships/{usr}'
        )
        resp = requests.get(url, headers=header)
        if resp.ok:
            # add user to admin
            user.is_superuser = True
            user.is_staff = True
            user.save()
            return {'user': user}


def debug(strategy, backend, uid, response, details, user, social, *args, **kwargs):
    print(response)
    pass


def load_github_avatar(response, social, *args, **kwargs):
    # assume github-team backend, add <if backend.name == 'github-team'>
    # if other backend are implemented
    # if social and social.get('extra_data', None)
    # print(vars(social))
    if 'avatar_url' not in social.extra_data:
        social.extra_data['avatar_url'] = response['avatar_url']
        social.save()
        return {'social': social}
    pass
