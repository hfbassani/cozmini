from event_messages import event_log, EventType
from flask import Flask, request, render_template_string
import threading
import webbrowser
from time import sleep
import logging

_log = logging.getLogger('werkzeug')
_log.setLevel(logging.ERROR)

_flask_app = Flask(__name__)
_flask_app.debug = False

class UserInterface():

    def __init__(self):
        self.new_user_input_provided = False
        self.user_says = ''
        self.history = ''

        _flask_app.add_url_rule('/', view_func=self.handle_index_page, methods=['GET'])
        _flask_app.add_url_rule('/handle_input', view_func=self.handle_input, methods=['POST'])
        _flask_app.add_url_rule('/get_history', view_func=self.get_history, methods=['GET'])

        self.input_page = '''
        <html>
            <script src="//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js"></script>
            <textarea
                    id="history"
                    name="history"
                    rows="15"
                    cols="180"
                    >{{ history }}</textarea>        
            <p>Say something to Cozmo</p>

            <form method="post" action="{{ url_for('handle_input') }}">
                <input id='input_box' type="text" name="user_says" value=""></input> <button type="submit">Say it</button>
            </form>

            <script>
                $("#input_box").focus();
                setInterval(function(){
                        $.ajax({
                        url:"{{ url_for('get_history') }}",
                        method:"GET",
                        success:function(data){
                            var $textarea = $("#history");
                            $textarea.val(data);
                            $textarea.scrollTop($textarea[0].scrollHeight);
                        }
                    });
                }, 250);
            </script>
        <html>
        '''
 
    def handle_index_page(self):
        return render_template_string(self.input_page, history=self.history)

    def handle_input(self):
        if request.method == 'POST':
            self.user_says = request.form['user_says']
            if self.user_says:
                event_log.message(EventType.USER_MESSAGE, self.user_says)                
                self.new_user_input_provided = True

        return render_template_string(self.input_page, user_says='', history=self.history)

    def get_history(self):
        return self.history
        
    def output_messges(self, messages):
        self.history += messages

    def capture_user_input(self):
        self.new_user_input_provided = False
        while not self.new_user_input_provided:
            sleep(0.05)
        return self.user_says

    def start_ui_loop(self):
        threading.Thread(target=lambda: self.run_flask(_flask_app), daemon=True).start()
    
    def run_flask(self, flask_app, host_ip="127.0.0.1", host_port=5000, open_page_delay=1.0):
        '''
        Run the Flask webserver on specified host and port
        optionally also open that same host:port page in your browser to connect
        '''
        url = "http://" + host_ip + ":" + str(host_port)
        # self.delayed_open_web_browser(url=url, delay=open_page_delay)
        print(f'User this URL to open the UI: {url}')

        flask_app.run(host=host_ip, port=host_port, use_evalex=False, threaded=True)

    def delayed_open_web_browser(self, url, delay, new=0, autoraise=True, specific_browser=None):
        '''
        Spawn a thread and call sleep_and_open_web_browser from within it so that main thread can keep executing at the
        same time. Insert a small sleep before opening a web-browser
        this gives Flask a chance to start running before the browser starts requesting data from Flask.
        '''

        def sleep_and_open_web_browser(url, delay, new, autoraise, specific_browser):
            sleep(delay)
            browser = webbrowser

            # E.g. On OSX the following would use the Chrome browser app from that location
            # specific_browser = 'open -a /Applications/Google\ Chrome.app %s'
            if specific_browser:
                browser = webbrowser.get(specific_browser)

            browser.open(url, new=new, autoraise=autoraise)

        thread = threading.Thread(target=sleep_and_open_web_browser,
                        kwargs=dict(url=url, new=new, autoraise=autoraise, delay=delay, specific_browser=specific_browser), daemon=True)
        thread.start()
