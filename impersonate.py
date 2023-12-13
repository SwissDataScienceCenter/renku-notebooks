import requests
from bs4 import BeautifulSoup
from keycloak import KeycloakAdmin


# Login as admin
admin_api = KeycloakAdmin(
    "https://renkulab.io/auth/", username="admin", password="xxx"
)

session = requests.Session()

res1 = session.post(
    "https://renkulab.io/auth/admin/realms/Renku/users/c3104af7-1fbb-4e1f-b0bf-f17a4c10d1ef/impersonation",
    headers={"Authorization": "bearer " + admin_api.connection.token["access_token"]},
    allow_redirects=True,
)
print(res1.text)
print(res1.status_code)

res2 = session.get("https://renkulab.io/api/auth/login", allow_redirects=True)
print(res2.text)
print(res2.status_code)
print(session.cookies)

if res2.status_code == 200 and "If you are not redirected automatically" in res2.text:
    soup = BeautifulSoup(res2.content, "html.parser")
    links = soup.find_all("a", {"class": "btn-rk-green"})
    res3 = session.get(links[0].attrs["href"], allow_redirects=True)
    print(res3.status_code)
    print(res3.text)

    if res3.status_code == 200 and '<h3 class="page-title">Redirecting</h3>' in res3.text:
        soup = BeautifulSoup(res3.content, "html.parser")
        links = soup.find_all("a")
        res4 = session.get(links[0].attrs["href"], allow_redirects=True)
        print(res4.status_code)
        print(res4.text)
    
        print(session.cookies)