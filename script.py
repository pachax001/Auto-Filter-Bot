from config import Config
class Script(object):

    START_MSG = """<b>Hi {},

I'm an advanced filter bot with many capabilities!
There is no practical limits for my filtering capacity :)

See <i>/help</i> for commands and more details.</b>
"""


    HELP_MSG = """
<b>What is a filter bot?</b>
<i>A bot where group admins can set replies for a particular keyword and the bot will automatically send preset replies whenever that keyword enountered in the chat.</i>

Usual commands:
/start - <code>check whether im online</code>
/help - <code>get this help message</code>
/about - <code>about me</code>
"""


    ABOUT_MSG = """⭕️<b>My Name : {}</b>

⭕️<b>Creator :</b> @gunaya001  

⭕️<b>Language :</b> <code>Python3</code>

⭕️<b>Library :</b> <a href='https://pyrofork.mayuri.my.id/main/'>Pyrofork</a> 

"""
    FILTER_HELP = f"""
<b>Filters:</b>
Filter is the feature where users can set automated replies for a particular keyword and the bot will respond whenever a keyword is found the message

<b>NOTE:</b>
<i>1. bot should have admin privillage in order to reply filters in a chat.
2. only admins can add filters in a chat.
3. filters does support all the telegram markdowns, medias and buttons.
4. alert buttons are also supported with a limit of 64 characters.
5. there are some easter eggs, try to find it out.</i>

Commands and Usage:
/{Config.ADD_FILTER_CMD}   - <code>add a filter</code>
/{Config.VIEW_FILTERS_COMMAND} - <code>list all the filters of a chat</code>
/{Config.DELETE_FILTER_CMD}  - <code>delete a specific filter (separate keywords with spaces for deleting multiple filters at a time)</code>
/{Config.DELETE_ALL_CMD} - <code>delete the whole filters in a chat (chat owner only)</code>
"""
    BUTTON_HELP = """
<b>Buttons:</b>
<i>@{} supports both url and alert inline buttons, now lets see how to implement it.</i>

<b>NB:</b>
1. Telegram will not allows you to send buttons without any content, so content is mandatory.
2. This bot supports buttons with any telegram media type.
3. Buttons should be properly formatted as below or else result will be malformed.

<b>URL buttons:</b>
<code>[Button Text](buttonurl://t.me/gunaya001)</code>

<b>Alert buttons:</b>
<code>[Button Text](buttonalert:Ahoy, this is an alert!)</code>
"""
    CONNECTION_HELP = f"""
<b>Connections:</b>>
Used to connect bot to PM which let will you to execute both normal filter related commands and some other sensitive commands right from the PM that will
reflect in the group which helps you to keep the filter additions and other stuffs private and helps to prevent flooding.

<b>NOTE:</b>
<i>1. Only admins can add a connection.
2. In a chat you can simply use the /connect for starting a connection and in PM you must specify chat id right after the command.</i>

Commands and Usage:
/{Config.CONNECT_COMMAND}  - <code>connect a particular chat to your PM</code>
/{Config.DISCONNECT_COMMAND}  - <code>disconnect from a chat</code>
/connections - <code>list all your connections</code>
"""
    OTHER_HELP = f"""
<b>Utilities:</b>

/id - <code>get the chat id of a user or the current chat</code>
/info  <code>whois info of a user who already started the bot and SAVE_USER is enabled</code>
"""
