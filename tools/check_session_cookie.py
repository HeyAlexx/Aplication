"""Check the anonymous loopback health cookie before enabling public HTTPS access.

Never sends credentials or follows redirects; outputs attributes, never cookie/token values.
"""
import argparse
import http.client
from http.cookies import CookieError, SimpleCookie
import json
from urllib.parse import parse_qs, urlsplit

from runtime_spec import PHP_VERSION

def evaluate(status,headers,body):
    if status!=200:raise ValueError('HEALTH_HTTP_STATUS')
    try:data=json.loads(body)
    except (ValueError,UnicodeError):raise ValueError('INVALID_HEALTH_RESPONSE') from None
    app=data.get('data') if isinstance(data,dict) else None
    if (not isinstance(data,dict) or data.get('ok') is not True or not isinstance(app,dict) or app.get('app')!='Altoidss API'
            or app.get('status')!='ok' or app.get('phpVersion')!=PHP_VERSION):
        raise ValueError('UNEXPECTED_HEALTH_RESPONSE')
    matches=[]
    for name,value in headers:
        if name.casefold()!='set-cookie':continue
        cookie=SimpleCookie()
        try:cookie.load(value)
        except CookieError:raise ValueError('INVALID_COOKIE_HEADER') from None
        if 'altoidss_session' in cookie:matches.append(cookie['altoidss_session'])
    if len(matches)!=1:raise ValueError('EXPECTED_SINGLE_SESSION_COOKIE')
    c=matches[0]
    result={'secure':bool(c['secure']),'httpOnly':bool(c['httponly']),'sameSite':c['samesite'],
        'path':c['path'],'hostOnly':not bool(c['domain'])}
    if result!={'secure':True,'httpOnly':True,'sameSite':'Lax','path':'/','hostOnly':True}:
        raise ValueError('UNSAFE_SESSION_COOKIE_ATTRIBUTES')
    return {'status':'PUBLIC_SESSION_COOKIE_VERIFIED','attributes':result,'cookieValuesEmitted':False,
        'externalHttpsVerified':False}

def check(url):
    target=urlsplit(url)
    if (target.scheme!='http' or target.hostname not in {'127.0.0.1','localhost','::1'} or target.username
            or target.password or target.fragment or target.path!='/api/index.php'
            or parse_qs(target.query,keep_blank_values=True)!={'route':['/health']}):
        raise ValueError('ONLY_LOOPBACK_HEALTH_ALLOWED')
    client=http.client.HTTPConnection(target.hostname,target.port or 80,timeout=5)
    try:
        client.request('GET','/api/index.php?route=/health')
        response=client.getresponse();body=response.read(65537)
        if len(body)>65536:raise ValueError('HEALTH_RESPONSE_TOO_LARGE')
        return evaluate(response.status,response.getheaders(),body)
    finally:client.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',required=True)
    args=parser.parse_args()
    try:result=check(args.url)
    except (ValueError,OSError,http.client.HTTPException):
        print(json.dumps({'status':'PUBLIC_SESSION_COOKIE_CHECK_FAILED','cookieValuesEmitted':False}));return 1
    print(json.dumps(result));return 0

if __name__=='__main__':raise SystemExit(main())
