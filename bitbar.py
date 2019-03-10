#!/usr/bin/env PYTHONIOENCODING=UTF-8 python3
# <bitbar.title>Icinga2 Advanced</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Sebastian Czoch</bitbar.author>
# <bitbar.author.github>SebastianCzoch</bitbar.author.github>
# <bitbar.desc>Icinga2 monitoring BitBar plugin</bitbar.desc>
# <bitbar.image>https://github.com/SebastianCzoch/icinga2-bitbar/blob/master/assets/bitbar.png?raw=true</bitbar.image>
# <bitbar.dependencies>python3,requests</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/SebastianCzoch/icinga2-bitbar</bitbar.abouturl>

import requests, json, os, sys
from requests.packages.urllib3.exceptions import InsecureRequestWarning

config = {
    "icinga2_address": "https://example.com",
    "icinga2_port": 5665,
    "icinga2_user": "root",
    "icinga2_password": "admin",
    "verify_ssl": False,
}

STATE_SERVICE_OK = 0
STATE_SERVICE_WARNING = 1
STATE_SERVICE_CRITICAL = 2
STATE_SERVICE_UNKNOWN = 3
STATE_HOST_UP = 0
STATE_HOST_DOWN = 1
SCRIPT_PATH = os.path.realpath(__file__)
COLOR_OK = "#009933"
COLOR_WARNING = "#ff9900"
COLOR_UNKNOWN = "#660066"
COLOR_CRITICAL = "#ff0000"

if not config["verify_ssl"]:
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def __get_hosts():
    return __make_get("/v1/objects/hosts")


def __get_services():
    return __make_get("/v1/objects/services")


def __make_post(path, data=None):
    return __make_request(method="POST", path=path, data=data)


def __make_get(path):
    return __make_request(path=path)


def __exit_with_error(e):
    print("ERROR | color=red")
    print(e)
    sys.exit(1)


def __make_request(method="GET", path="/", data=None):
    try:
        params = {**config, **{"path": path}}
        headers = {"Accept": "application/json"}
        if method == "GET":
            headers = {**headers, **{"X-HTTP-Method-Override": "GET"}}

        r = requests.post(
            url="{icinga2_address}:{icinga2_port}{path}".format(**params),
            headers=headers,
            verify=config["verify_ssl"],
            auth=(config["icinga2_user"], config["icinga2_password"]),
            json=data,
        )

        if r.status_code != 200:
            __exit_with_error(r)

        return json.loads(json.dumps(r.json()))["results"]
    except Exception as e:
        __exit_with_error(e)


def __filter_by_state(objects, state):
    return [i for i in objects if i["attrs"]["state"] == state]


def __filter_by_ack(objects, is_acked):
    return [i for i in objects if i["attrs"]["acknowledgement"] == int(is_acked)]


def __get_color_for_item(item):
    if item["type"] == "Service":
        if item["attrs"]["state"] == STATE_SERVICE_CRITICAL:
            return COLOR_CRITICAL
        if item["attrs"]["state"] == STATE_SERVICE_UNKNOWN:
            return COLOR_UNKNOWN
        if item["attrs"]["state"] == STATE_SERVICE_WARNING:
            return COLOR_WARNING

    if item["type"] == "Host":
        if item["attrs"]["state"] == STATE_HOST_DOWN:
            return COLOR_CRITICAL

    return COLOR_OK


def __print_service(item):
    print(
        "{} - {} | color={}".format(
            item["attrs"]["display_name"],
            item["attrs"]["host_name"],
            __get_color_for_item(item),
        )
    )
    print(
        '--Acknowledge | bash={} param2=ack param3=service param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )

    print(
        '--Check now | bash={} param2=recheck param3=service param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )


def __print_service_acked(item):
    print(
        "--{} - {} | color={}".format(
            item["attrs"]["display_name"],
            item["attrs"]["host_name"],
            __get_color_for_item(item),
        )
    )
    print(
        '----Remove acknowledgement | bash={} param2=remove_ack param3=service param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )

    print(
        '----Check now | bash={} param2=recheck param3=service param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )


def __print_host(item):
    print(
        "{} | color={}".format(
            item["attrs"]["display_name"], __get_color_for_item(item)
        )
    )
    print(
        '--Acknowledge | bash={} param2=ack param3=host param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )

    print(
        '--Check now | bash={} param2=recheck param3=host param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )


def __print_host_acked(item):
    print(
        "--{} | color={}".format(
            item["attrs"]["display_name"], __get_color_for_item(item)
        )
    )
    print(
        '----Remove acknowledgement | bash={} param2=remove_ack param3=host param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )

    print(
        '----Check now | bash={} param2=recheck param3=host param4="{}" terminal=false refresh=true'.format(
            SCRIPT_PATH, item["attrs"]["__name"]
        )
    )


def __recheck(name, kind):
    r = __make_post("/v1/actions/reschedule-check?{}={}".format(kind, name))


def __ack(name, kind):
    r = __make_post(
        "/v1/actions/acknowledge-problem?{}={}".format(kind, name),
        data={"author": config["icinga2_user"], "comment": " "},
    )


def __remove_ack(name, kind):
    r = __make_post("/v1/actions/remove-acknowledgement?{}={}".format(kind, name))


if "ack" in sys.argv:
    __ack(sys.argv[3], sys.argv[2])
    sys.exit(0)

if "remove_ack" in sys.argv:
    __remove_ack(sys.argv[3], sys.argv[2])
    sys.exit(0)


if "recheck" in sys.argv:
    __recheck(sys.argv[3], sys.argv[2])
    sys.exit(0)

hosts = __get_hosts()
services = __get_services()
critical_services = __filter_by_ack(
    __filter_by_state(services, STATE_SERVICE_CRITICAL), False
)
critical_services_acked = __filter_by_ack(
    __filter_by_state(services, STATE_SERVICE_CRITICAL), True
)

unknown_services = __filter_by_ack(
    __filter_by_state(services, STATE_SERVICE_UNKNOWN), False
)
unknown_services_acked = __filter_by_ack(
    __filter_by_state(services, STATE_SERVICE_UNKNOWN), True
)

warning_services = __filter_by_ack(
    __filter_by_state(services, STATE_SERVICE_WARNING), False
)
warning_services_acked = __filter_by_ack(
    __filter_by_state(services, STATE_SERVICE_WARNING), True
)

down_hosts = __filter_by_ack(__filter_by_state(hosts, STATE_HOST_DOWN), False)
down_hosts_acked = __filter_by_ack(__filter_by_state(hosts, STATE_HOST_DOWN), True)

main_color = COLOR_OK
if len(warning_services) > 0:
    main_color = COLOR_WARNING
if len(unknown_services) > 0:
    main_color = COLOR_UNKNOWN
if len(critical_services) + len(down_hosts) > 0:
    main_color = COLOR_CRITICAL

print(
    "D: {} C: {} U: {} W: {} | color={}".format(
        len(down_hosts),
        len(critical_services),
        len(unknown_services),
        len(warning_services),
        main_color,
    )
)
print("---")
print("Hosts: {}".format(len(hosts)))
print("Services: {}".format(len(services)))

# Hosts down
if len(down_hosts) + len(down_hosts_acked):
    print("---")
    print("Host problems")
    [__print_host(s) for s in down_hosts]
    if len(down_hosts_acked) != 0:
        print("Acknowledged hosts down {}".format(len(down_hosts_acked)))
        [__print_host_acked(s) for s in down_hosts_acked]

if (
    len(critical_services)
    + len(critical_services_acked)
    + len(unknown_services)
    + len(unknown_services_acked)
    + len(warning_services)
    + len(warning_services_acked)
    > 0
):
    print("---")
    print("Service problems")

# Critical services
if len(critical_services) + len(critical_services_acked):
    [__print_service(s) for s in critical_services]
    if len(critical_services_acked) != 0:
        print("Acknowledged critical services {}".format(len(critical_services_acked)))
        [__print_service_acked(s) for s in critical_services_acked]

# Unknown services
if len(unknown_services) + len(unknown_services_acked):
    [__print_service(s) for s in unknown_services]
    if len(unknown_services_acked) != 0:
        print("Acknowledged unknown services {}".format(len(unknown_services_acked)))
        [__print_service_acked(s) for s in unknown_services_acked]

# Warning services
if len(warning_services) + len(warning_services_acked):
    [__print_service(s) for s in warning_services]
    if len(warning_services_acked) != 0:
        print("Acknowledged warning services {}".format(len(warning_services_acked)))
        [__print_service_acked(s) for s in warning_services_acked]

print("---")
print("Refresh | refresh=true")
