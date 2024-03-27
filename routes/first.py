"""Copyright 2023 TimeEnjoyed <https://github.com/TimeEnjoyed/>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse

from api import View, route

if TYPE_CHECKING:
    
    from api import Server

# this api endpoint just returns the longest streak (json) of a particular twitch user

logger: logging.Logger = logging.getLogger(__name__)

class Redeems(View):
    def __init__(self, app: Server) -> None:
        self.app = app
    
    # @route("/first", methods=["GET"])
    # async def get_first_streak(self, )
        #  {"name": "user_name_here", "count": 214123452145}
       """ <!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">

    <title>OBS - "First" Redeem Page</title>

    <!-- PACKAGES -->
    <script src="/static/packages/htmx.min.js"></script>
    <!-- SCRIPTS -->
    <script src="/static/scripts.js"></script>
    <!-- STYLES -->
    <link rel="stylesheet" href="/static/styles.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
</head>

<body hx-sse="connect:/sse/player">
  <div></div>
</body>

</html>"""
    