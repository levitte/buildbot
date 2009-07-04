import urllib

from twisted.python import log
from twisted.web import client, error
from twisted.application import service

from buildbot import status

class WebHookTransmitter(status.base.StatusReceiverMultiService):

    agent = 'buildbot webhook'

    def __init__(self, url, categories=None, extra_params={}):
        status.base.StatusReceiverMultiService.__init__(self)
        if isinstance(url, basestring):
            self.urls = [url]
        else:
            self.urls = url
        self.categories = categories
        self.extra_params = extra_params

    def _transmit(self, event, params={}):
        new_params = [('event', event)]
        new_params.extend(list(self.extra_params.items()))
        if hasattr(params, "items"):
            new_params.extend(params.items())
        else:
            new_params.extend(params)
        encoded_params = urllib.urlencode(new_params)

        def _trap_status(x, *acceptable):
            x.trap(error.Error)
            if int(x.value.status) in acceptable:
                return None
            else:
                return x

        log.msg("WebHookTransmitter announcing a %s event" % event)
        for u in self.urls:
            d = client.getPage(u, method='POST', agent=self.agent,
                               postdata=encoded_params, followRedirect=0)
            d.addErrback(lambda x: x.trap(error.PageRedirect))
            d.addErrback(_trap_status, 204)
            d.addCallback(lambda x: log.msg("Completed %s event hook" % event))
            d.addErrback(log.err)

    def builderAdded(self, builderName, builder):
        builder.subscribe(self)
        self._transmit('builderAdded',
                       {'builder': builderName,
                        'category': builder.getCategory()})

    def builderRemoved(self, builderName, builder):
        self._transmit('builderRemoved',
                       {'builder': builderName,
                        'category': builder.getCategory()})


    def buildStarted(self, builderName, build):
        build.subscribe(self)
        self._transmit('buildStarted',
                       {'builder': builderName,
                        'category': build.getBuilder().getCategory(),
                        'reason': build.getReason(),
                        'sourceStamp': ' '.join(build.getSourceStamp().getText()),
                        'buildNumber': build.getNumber()})

    def buildFinished(self, builderName, build, results):
        self._transmit('buildFinished',
                       {'builder': builderName,
                        'category': build.getBuilder().getCategory(),
                        'result': status.builder.Results[results],
                        'sourceStamp': ' '.join(build.getSourceStamp().getText()),
                        'buildNumber': build.getNumber()})

    def stepStarted(self, build, step):
        step.subscribe(self)
        self._transmit('stepStarted',
                       [('builder', build.getBuilder().getName()),
                        ('category', build.getBuilder().getCategory()),
                        ('buildNumber', build.getNumber()),
                        ('step', step.getName())])

    def stepFinished(self, build, step, results):
        gu = self.status.getURLForThing
        self._transmit('stepFinished',
                       [('builder', build.getBuilder().getName()),
                        ('category', build.getBuilder().getCategory()),
                        ('buildNumber', build.getNumber()),
                        ('resultStatus', status.builder.Results[results[0]]),
                        ('resultString', ' '.join(results[1])),
                        ('step', step.getName())]
                       + [('logFile', gu(l)) for l in step.getLogs()])

    def _subscribe(self):
        self.status.subscribe(self)

    def setServiceParent(self, parent):
        status.base.StatusReceiverMultiService.setServiceParent(self, parent)
        self.status = parent.getStatus()

        self._transmit('startup')

        self._subscribe()
