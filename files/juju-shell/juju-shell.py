"""A single common terminal for all websockets.
"""
import os
from tornado import (
    ioloop,
    web,
)
# This demo requires tornado_xstatic and XStatic-term.js
import tornado_xstatic

import terminado
from terminado import TermSocket, SingleTermManager


STATIC_DIR = os.path.join(os.path.dirname(terminado.__file__), "_static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


class TerminalPageHandler(web.RequestHandler):
    def get(self):
        return self.render("termpage.html", static=self.static_url,
                           xstatic=self.application.settings['xstatic_url'],
                           ws_url_path="/websocket")


def main(argv):
    term_manager = terminado.SingleTermManager(shell_command=['bash'])
    handlers = [
                (r"/websocket", terminado.TermSocket,
                     {'term_manager': term_manager}),
                (r"/", TerminalPageHandler),
                (r"/xstatic/(.*)", tornado_xstatic.XStaticFileHandler,
                     {'allowed_modules': ['termjs']})
               ]
    app = web.Application(handlers, static_path=STATIC_DIR,
                      template_path=TEMPLATE_DIR,
                      xstatic_url = tornado_xstatic.url_maker('/xstatic/'))
    app.listen(8765, '0.0.0.0')
    loop = ioloop.IOLoop.instance()
    try:
        loop.start()
    except KeyboardInterrupt:
        print(" Shutting down on SIGINT")
    finally:
        term_manager.shutdown()
        loop.close()


if __name__ == '__main__':
    main([])
