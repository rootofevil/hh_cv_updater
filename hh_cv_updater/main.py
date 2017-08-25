import requests, calendar, time, redis, logging
from dateutil import parser
from datetime import datetime

logging.basicConfig(format = u'%(levelname)-8s [%(asctime)s] %(message)s', level = logging.DEBUG, filename = 'updater.log')
redis = redis.Redis(unix_socket_path='/tmp/redis.sock')
access_token = redis.get('access_token')
auth_line = 'Bearer ' + access_token
headers = {'User-agent': 'Mozilla/5.0', 'Authorization': auth_line}
base_url = 'https://api.hh.ru'
update_url = 'https://hh.ru/oauth/token'

def get_ca_ids():
    method = '/resumes/mine'
    r = requests.get(url = base_url+method, headers = headers)
    if r.status_code == 200:
        res = r.json()
        items = res['items']
        ca_list = list()        
        for item in items:
            if item['status']['id'] == 'published':
                resume_id = item['id']
                #update_resume(resume_id)
                ca_list.append(resume_id)
        return ca_list
    else:
        error_handler(r)
        

def update_all_cas():
    ids = get_ca_ids()
    try:
        for id in ids:
            update_resume(id)
    except TypeError:
        logging.error("Cant Take Resume List")
        exit(1)

def update_resume(resume_id):
    method = '/resumes/' + resume_id + '/publish'
    r = requests.post(url = base_url + method, headers = headers)
    if r.status_code == 429:
        logging.info('Updating Not Availible Now. Will Be Repeate later.')
        method = '/resumes/'+resume_id
        r = requests.get(url = base_url + method, headers = headers)
        if r.status_code == 200:
            next_update = r.json()['next_publish_at']
            parsed_date = parser.parse(str(next_update))
            delta = calendar.timegm(parsed_date.timetuple()) - calendar.timegm(datetime.now().timetuple()) + 7200
            time.sleep(delta + 5)
            update_resume(resume_id)
    if r.status_code == 204:
        logging.info('Success')

def token_update():
    new_header = {'User-agent': 'Mozilla/5.0','Content-Type': 'application/x-www-form-urlencoded'}
    refresh_token = redis.get('refresh_token')
    data = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}
    r = requests.post(url = update_url, headers = new_header, data = data)
    data = r.json()
    redis.set('access_token', data['access_token'])
    redis.set('refresh_token', data['refresh_token'])
    if not r.ok:
        error_handler(r)
    
        
def error_handler(r):
    logging.error('Error handler: ' + str(r.status_code))
    data = r.json()
    error = data['errors'][0]
    error_description = data['description']
    logging.error('Error handler: ' + error_description)
    logging.error(error['value'])
    if error['type'] == 'oauth' and error['value'] == 'token_expired':
        logging.info("Error handler: we need update token")
        token_update()
        update_all_cas()
                
if __name__ == '__main__':
    update_all_cas()
