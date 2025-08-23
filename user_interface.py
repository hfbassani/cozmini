from event_messages import event_log, EventType
from flask import Flask, request, render_template_string, make_response, send_file
from io import BytesIO
import threading
import webbrowser
from time import sleep
import logging
import traceback

_log = logging.getLogger('werkzeug')
_log.setLevel(logging.ERROR)

_flask_app = Flask(__name__)
_flask_app.debug = False

class UserInterface():

    def __init__(self, get_image=None):
        self.new_user_input_provided = False
        self.user_says = ''
        self.current_input = ''
        self.history = ''
        self.get_image = get_image

        _flask_app.add_url_rule('/', view_func=self.handle_index_page, methods=['GET'])
        _flask_app.add_url_rule('/handle_input', view_func=self.handle_input, methods=['POST'])
        _flask_app.add_url_rule('/handle_partial_input', view_func=self.handle_partial_input, methods=['POST'])
        _flask_app.add_url_rule('/get_history', view_func=self.get_history, methods=['GET'])
        _flask_app.add_url_rule('/cozmoImage', view_func=self.handle_cozmoImage, methods=['GET'])

        self.input_page = '''
        <html>
            <script src="//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js"></script>
            <img src="cozmoImage" id="cozmoImageId" width=640 height=480>
            <textarea
                    id="history"
                    name="history"
                    rows="15"
                    cols="180"
                    >{{ history }}</textarea>        
            <p>Say something to Cozmo</p>

            <form method="post" action="{{ url_for('handle_input') }}">
                <input id='input_box' type="text" onchange="handleChange()" name="user_says" value=""></input> <button type="submit">Say it</button>
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
                    document.getElementById("cozmoImageId").src="cozmoImage?" + (new Date()).getTime();
                }, 250);

                function handleChange() {
                    const inputValue = document.getElementById('input_box').value;
                    $.ajax({
                        url:"{{ url_for('handle_partial_input') }}",
                        method:"POST",
                        data: {
                            current_input: inputValue
                        }
                    });
                }
        </script>
    </html>
    '''

    def handle_index_page(self):
        return render_template_string(self.input_page, history=self.history)

    def handle_input(self):
        if request.method == 'POST':
            self.user_says = request.form['user_says']
            self.current_input = ''
            if self.user_says:
                event_log.message(EventType.USER_MESSAGE, self.user_says)                
                self.new_user_input_provided = True

        return render_template_string(self.input_page, user_says='', history=self.history)

    def handle_partial_input(self):
        if request.method == 'POST':
            self.current_input = request.form.get('current_input', '')

        return render_template_string(self.input_page, user_says='', history=self.history)

    def get_history(self):
        return self.history

    def output_messges(self, messages):
        self.history += messages

    def capture_user_input(self):
        self.new_user_input_provided = False
        self.history += "Cozmo is listening..."
        while not self.new_user_input_provided:
            sleep(0.05)
        return self.user_says

    def wait_input_finish(self):
        if self.current_input and self.new_user_input_provided:
            self.capture_user_input()

    def handle_cozmoImage(self):
        '''Convert PIL image to a image file and send it'''
        if self.get_image:
            try:
                image = self.get_image()
                if image:
                    if hasattr(image, 'annotate_image'):
                        image = image.annotate_image(scale=2)
                    img_io = BytesIO()
                    image.save(img_io, 'PNG')
                    img_io.seek(0)
                    return self.make_uncached_response(send_file(img_io, mimetype='image/png', etag=False))
            except Exception as e:
                traceback.print_exc()

        return render_template_string(self.input_page, user_says='', history=self.history)

    def make_uncached_response(self, in_file):
        response = make_response(in_file)
        response.headers['Pragma-Directive'] = 'no-cache'
        response.headers['Cache-Directive'] = 'no-cache'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    def start_loop(self):
        threading.Thread(target=lambda: self.run_flask(_flask_app), daemon=True).start()
    
    def run_flask(self, flask_app, host_ip="127.0.0.1", host_port=5000, open_page_delay=1.0):
        '''
        Run the Flask webserver on specified host and port
        optionally also open that same host:port page in your browser to connect
        '''
        url = "http://" + host_ip + ":" + str(host_port)
        # self.delayed_open_web_browser(url=url, delay=open_page_delay)
        print(f'Use this URL to open the UI: {url}')

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
