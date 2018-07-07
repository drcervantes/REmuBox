var messages = 1;
var session_id = "";

function getSessionId(s) {
    if (!s.fromUpstream) {
        if ( s.buffer.toString().length == 0 ) {
            s.log("No buffer yet");             
            return s.AGAIN;
        }
	else if (messages == 1) { 
            var packet_type = s.buffer.charCodeAt(5);
            s.log("RDP packet type = " + packet_type.toString());

	    if (packet_type == 224) {
		var i = 11;
		for (; i < s.buffer.length; i++) {
		    if (s.buffer[i] == "\x0D" && s.buffer[i+1] == "\x0A")
			break;
		    session_id += s.buffer[i]
		}
		s.log("Session ID = \"" + session_id + "\"");
	    }
	    else {
                s.log("Received unexpected RDP packet type: " + packet_type.toString());
            }
        }
        messages++;
    }
    return s.OK;
}

function setSessionId(s) {
    return session_id;
}
