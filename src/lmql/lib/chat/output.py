import lmql
from lmql.runtime.output_writer import BaseOutputWriter

class ChatMessageOutputWriter(BaseOutputWriter):
    """
    An output writer with additional methods to stream messages annotated as @lmql.lib.chat.message.

    See also `lmql.lib.chat.MessageDecorator`.
    """
    def begin_message(self, variable):
        pass

    def stream_message(self, message):
        pass

    def complete_message(self, message):
        pass

class MessageDecorator(lmql.decorators.LMQLDecorator):
    """
    Provides an @message variable decorator in queries, allowing them
    to specify what output variables are shown to the user (streamed as chat messages).

    To be used in conjunction with a `lmql.lib.chat.ChatMessageOutputWriter` output writer.
    """
    def pre(self, variable, context):
        if context.runtime.output_writer is not None and isinstance(context.runtime.output_writer, ChatMessageOutputWriter):
            context.runtime.output_writer.begin_message(variable)
        return variable

    def stream(self, variable_value, context):
        # invoke designated 'stream_message' method of output writer if it exists
        if context.runtime.output_writer is not None and isinstance(context.runtime.output_writer, ChatMessageOutputWriter):
            context.runtime.output_writer.stream_message(variable_value)

    def post(self, variable_value, prompt_value, context):
        if context.runtime.output_writer is not None and isinstance(context.runtime.output_writer, ChatMessageOutputWriter):
            context.runtime.output_writer.complete_message(variable_value)
        
        return super().post(variable_value, prompt_value, context)