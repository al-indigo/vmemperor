from flask import Flask
from flask import session as flask_session
from flask import render_template, json, jsonify
from flask import request

from xenadapter import XenAdapter

app = Flask(__name__, static_url_path='/static')

global preseed
preseed = dict()

global status_dict
status_dict = dict()





@app.route("/auth", methods=['POST'])
def authenticate():  # use outer authentication system tokens
    """Sends a 401 response that enables basic auth"""
    adapters = []
    counter = 0
    form = request.form if request.form else json.loads(request.data)
    for endpoint in app.config['xen_endpoints']:
        login = form['login' + str(counter)]
        password = form['password' + str(counter)]
        try:
            adapters.append(XenAdapter(endpoint, flask_session, login, password))
        except Exception as e:
            flask_session.clear()
            response = jsonify({'status': 'error', 'details': 'Auth failed',
                                'reason': str(e)})
            print(e)
            response.status_code = 401
            return response

    flask_session['is_su'] = all([endp["is_su"] for k, endp in flask_session.items()])

    response = jsonify({'status': 'ok', 'details': 'Auth successful', 'reason': 'ok'})
    response.status_code = 200
    return response


"""
def admin_authenticate():
    does what previous authenticate did


"""


"""
def list_vms():
    uses XenAdapter.get_vms_list()
"""



"""
def list_templates():
    uses XenAdapter.get_template_list()
    sort by
"""

@app.route('/list-vms')
def list_vms():
    vm_list = []
    for endpoint in app.config['xen_endpoints']:
        adapter = XenAdapter(endpoint, flask_session)
        vm_list.extend(adapter.get_vms_list())
    return jsonify(vm_list)

# should there be process, that checks system and updates info in database every n seconds(minutes) ?


@app.route('/list-templates')
def list_templates():  # requires to be logged in as an admin  (probably should cache this info into rethinkdb)
    template_list = []
    adapters = []
    for endpoint in app.config['xen_endpoints']:
        adapters.append(XenAdapter(endpoint, flask_session))

    if 'is_su' in flask_session and flask_session['is_su']:
        for adapter in adapters:
            template_list.extend(adapter.get_template_list())
        template_list = sorted(template_list, key=lambda k: (-len(k['tags']), k['name_label'].lower()))
    else:
        response = jsonify({'status': 'error', 'details': 'Failed to retrieve template list', 'reason': 'You have no pool administrator rights'})
        response.status_code = 401
        return response
    return jsonify(template_list)


"""
def list_templates():
    uses XenAdapter.retrieve_pool_info()
    sort by
"""

@app.route('/list-pools', methods=['GET'])  # (probably should cache this info into rethinkdb)
def list_pools():
    pool_list = []
    for endpoint in app.config['xen_endpoints']:
        adapter = XenAdapter(endpoint, flask_session)
        pool_info = adapter.retrieve_pool_info()
        pool_info.update(endpoint)
        pool_info['templates_enabled'] = [item for item in adapter.get_template_list() if 'tags' in item and 'vmemperor' in item['tags']]
        pool_list.append(pool_info)

    return jsonify(pool_list)


def on_off_dispatcher(req, action):
    form = req.form if req.form else json.loads(req.data)
    vm_uuid = form.get('vm_uuid')
    endpoint_url = form.get('endpoint_url')
    if not vm_uuid or not endpoint_url:
        response = {'status': 'error', 'details': 'Syntax error in your query', 'reason': 'missing argument'}
        response.status_code = 406
        return response

    endpoint = {'url': endpoint_url}
    adapter = XenAdapter(endpoint, flask_session)
    if action == "enable-template":
        response_dict, response_status = adapter.capture_template(vm_uuid, True)
    elif action == "disable-template":
        response_dict, response_status = adapter.capture_template(vm_uuid, False)
    elif action == "start-vm":
        response_dict, response_status = adapter.start_stop_vm(vm_uuid, True)
    elif action == "shutdown-vm":
        response_dict, response_status = adapter.start_stop_vm(vm_uuid, False)
    else:
        response_dict = {'status': 'error', 'details': 'Something wrong in internals', 'reason': 'missing argument'}
        response_status = 500

    response = jsonify(response_dict)
    response.status_code = response_status
    return response

"""
def create_vm():
    uses xenadapter.create_vm
"""


@app.route('/create-vm', methods=['POST'])
def create_vm():
    form = request.form if request.form else json.loads(request.data)
    print(form)
    """
    template-select -> template_uuid
    storage-select -> sr
    network-select  -> network_uuid
    add os_kind argument
    """

    if not form.get("template-select") or \
        not form.get("pool-select") or \
        form.get("template-select") == "--" or \
        form.get("pool-select") == "--" or \
        not form.get("username") or \
        not form.get("hostname") or \
        not form.get("password"):
        response = jsonify({'status': 'error', 'details': 'You have missing obligatory argument', 'reason': 'missing argument'})
        response.status_code = 400
        return response
    if form.get("password") != form.get("password2"):  # check by token prior to view
        response = jsonify({'status': 'error', 'details': 'Your passwords do not match', 'reason': 'wrong argument'})
        response.status_code = 400
        return response

    endpoint = {'url': form["pool-select"]}
    adapter = XenAdapter(endpoint, flask_session)

    vm, mirror_url, mirror_path = adapter.create_vm(form["template-select"], form["hostname"], form["vcpus"], int(form["ram"])*1024*1024, form["hdd"], form["storage-select"], form["network-select"], "ubuntu", app.config['vmemperor-address'] + "preseed")

    preseed[vm] = form
    preseed[vm]["mirror_url"] = mirror_url
    preseed[vm]["mirror_path"] = mirror_path

    response = jsonify({"uuid": vm})
    status_dict[vm] = ("System installation initiated", 20)
    response.status_code = 200
    return response


"""
def get_preseed():
    todo
"""

@app.route('/preseed/<oskind>/<id>')
def get_preseed(oskind, id):
    return render_template("installation-scenarios/ubuntu.jinja2", opts=preseed[id])

"""
def get_status():
    use status in rethinkdb
    todo
"""


"""
def statistic loop():
    periodically asks everything about their status and updates rethinkdb
"""


@app.route('/status-vm', methods=['POST'])
def get_status():  # use rethinkdb
    form = request.form if request.form else json.loads(request.data)
    status_d = {}
    for vm in form['ids']:
        if status_dict.get(vm):
            status_d[vm] = {"name": vm, "status": status_dict[vm][0], "details": status_dict[vm][1]}

    return jsonify(status_d)

"""
def start_vm():
    adapter.start_stop_vm
"""

@app.route('/start-vm', methods=['POST'])  # rename to start_vm
def start_vm():
    return on_off_dispatcher(request, "start-vm")

"""
def shutdown_vm():
    adapter.start_stop_vm
"""

@app.route('/shutdown-vm', methods=['POST'])  # rename to shutdown_vm
def shutdown_vm():
    return on_off_dispatcher(request, "shutdown-vm")


"""
def enable_template():
    adapter.capture_template
"""
@app.route('/enable-template', methods=['POST'])  # rename to enable_template
def enable_template():
    return on_off_dispatcher(request, "enable-template")


"""
def disable_template():
    adapter.capture_template
"""
@app.route('/disable-template', methods=['POST'])  # rename to disable_template
def disable_template():
    return on_off_dispatcher(request, "disable-template")


"""
def disable_template():
    adapter.set_install_options
"""

@app.route('/update-template', methods=['POST'])  # rename to update_template
def update_template():
    form = request.form if request.form else json.loads(request.data)
    vm_uuid = form.get('vm_uuid')
    endpoint_url = form.get('endpoint_url')
    mirror = form.get('default_mirror')
    hooks_dict = form.get('vmemperor_hooks')
    endpoint = {'url': endpoint_url}
    adapter = XenAdapter(endpoint, flask_session)
    response_dict, response_status = adapter.set_install_options(vm_uuid, hooks_dict, mirror)
    response = jsonify(response_dict)
    response.status_code = response_status
    return response


@app.route('/logout', methods=['POST', 'GET'])  # removes token from cookies
def logout():
    flask_session.clear()
    response = jsonify({'status': 'success', 'details': 'Logout successful', 'reason': ''})
    response.status_code = 200
    return response

"""
def list_vdi()
    lists vdi
"""


"""
def create_vbd():
    gets vm uuid and vbi uuid and creates vbd

"""

"""
def plug_vbd():
    gets vbd uuid and plugs it in associated vm

"""

"""
def add_hook():
    gets ansible file and variables template from user and stores it
    think harder
"""


"""
def use_hook():
    gets information about which vm to run which ansible playbook onto
    gets information for variables template and launches ansible playbook
    think harder
"""


"""
def get_vnc_connection():
    http://xapi-project.github.io/xen-api/consoles.html
    think harder
"""


@app.route('/')
def secret_page():
    return render_template('index.html')


@app.route('/pool-index', methods=["GET"])
def pool_index():
    return jsonify(app.config['xen_endpoints'])


#app.secret_key = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
app.secret_key = 'SADFccadaeqw221fdssdvxccvsdf'
if __name__ == '__main__':  # everything should be loaded from ini
    #app.config.update(SESSION_COOKIE_SECURE=True)
    app.config['SESSION_COOKIE_HTTPONLY'] = False
    app.config['xen_endpoints'] = [
        {'id': 'http://10.10.10.18:80/', 'url': 'http://10.10.10.18:80/', 'description': 'Pool A'},
        #{'id': 'http://10.10.10.18:80//', 'url': 'http://10.10.10.18:80/', 'description': 'Pool Z'},
        #{'id': 'http://172.31.0.32:80/', 'url': 'http://172.31.0.32:80/', 'description': 'Pool Z'}
        ]
    app.config['supported-distros'] = {'debianlike': 'all'}
    app.config['enabled-distros'] = app.config['supported-distros']
    app.config['supported-reverse-proxies'] = {'vmemperor-nginx': 'Nginx configuration files'}
    app.config['enabled-reverse-proxies'] = app.config['supported-reverse-proxies']
    app.config['vmemperor-address'] = 'http://localhost:5000/'
    #retrieve_vms_list(session)
    app.run(debug=True, use_reloader=True, threaded=False, host="0.0.0.0", port=5000)
