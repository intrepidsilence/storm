import getpass


def split_uri(uri):
    """
    splits an ssh connection uri into (user, host, port), leaving out the
    parts that are not in the uri as None. the port is validated and
    returned as an int.

    IPv6 addresses go in brackets when a port follows them:
        - [2001:db8::1]:2222, root@[::1]
        - a bare address without a port works too: root@2001:db8::1
    """
    uri = uri.strip()
    user = None
    port = None

    if '@' in uri:
        user, uri = uri.rsplit('@', 1)

    if uri.startswith('['):
        host, bracket, rest = uri[1:].partition(']')
        if not bracket or (rest and not rest.startswith(':')):
            raise ValueError("invalid IPv6 address: use [address] or [address]:port.")
        if rest:
            port = rest[1:]
    elif uri.count(':') > 1:
        # a bare IPv6 address; its colons are not a port separator
        host = uri
    else:
        host, colon, port_text = uri.partition(':')
        if colon:
            port = port_text

    if port is not None:
        try:
            port = int(port)
        except ValueError:
            raise ValueError("port must be numeric.") from None

        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535.")

    if not host:
        raise ValueError("host cannot be empty.")

    return user, host, port


def format_uri(user, host, port):
    """
    the inverse of parse: builds user@host:port, bracketing IPv6 hosts so
    the port can be told apart from the address.
    """
    if ':' in str(host):
        host = f"[{host}]"
    return f"{user}@{host}:{port}"


def parse(uri, user=None, port=22):
    """
    parses ssh connection uri-like sentences.
    ex:
        - root@emreyilmaz.me:22 -> (root, emreyilmaz.me, 22)
        - noreply@facebook.com:22 -> (noreply, facebook.com, 22)
        - facebook.com:3306 -> ($USER, facebook.com, 3306)
        - twitter.com -> ($USER, twitter.com, 22)
        - root@[2001:db8::1]:2222 -> (root, 2001:db8::1, 2222)

    default port: 22
    default user: $USER (getpass.getuser())
    """
    uri_user, host, uri_port = split_uri(uri)

    if uri_user is not None:
        user = uri_user
    elif not user:
        user = getpass.getuser()

    if uri_port is not None:
        port = uri_port

    try:
        port = int(port)
    except ValueError:
        raise ValueError("port must be numeric.") from None

    return (user, host, port)
