import logging
import requests


def save_profile(backend, user, response, *args, **kwargs):
    # print(' '.join(40 * ['*']))
    # print(backend.name)
    # print(response)
    # print(response.get('email', None))
    # if backend.name == 'facebook':
    #     profile = user.get_profile()
    #     if profile is None:
    #         profile = Profile(user_id=user.id)
    #     profile.gender = response.get('gender')
    #     profile.link = response.get('link')
    #     profile.timezone = response.get('timezone')
    #     profile.save()

    # print(' '.join(40 * ['*']))
    pass

def check_admin_user(uid, response, details, user, social, *args, **kwargs):
    print(' '.join(40 * ['=']))
    # print(response)
    admin_team = 'vast-data-admin'
    # user = 'srggrs'
    # user = 'srggrs-test'
    usr = response.get('url', '')
    if usr != '':
        usr = usr.split('/')[-1]
    print(usr)
    org = 'askap-vast'
    header = {
        'Authorization': f"token {response.get('access_token', '')}"
    }
    url = (
        f'https://api.github.com/orgs/{org}/teams/{admin_team}'
        f'/memberships/{usr}'
    )
    resp = requests.get(url, headers=header)
    # print(resp.status_code)
    # print(resp.ok)
    if resp.ok:
        print('response text', resp.text)
        print(' '.join(20 * ['-']))
        print('details', details)
        print(' '.join(20 * ['-']))
        print('user', user)
        # profile = user.get_profile()
        print(vars(user))
        print(dir(user))
        # set superuser attributes
        user.is_superuser = True
        user.is_staff = True
        print(' '.join(20 * ['-']))
        print('social', social)
        # add user to admin
    # check if github user belong to team
    # print(request)
    # print(details)
    # print(response)

    print(' '.join(40 * ['=']))
    pass

def debug(strategy, backend, uid, response, details, user, social, *args, **kwargs):
    print(response)
    pass
