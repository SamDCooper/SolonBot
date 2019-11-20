import discord
import solon

cypher_settings = {
    "alphabet": {"value_serialized": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVW", "type_name": "str"},
    "max_length": {"value_serialized": "3", "type_name": "int"},
    "cypher": {"value_serialized": "102316", "type_name": "int"},
    "offset": {"value_serialized": "-2464", "type_name": "int"}
}


@solon.Cog(default_active=True, default_settings=cypher_settings)
class Cypher(discord.ext.commands.Cog):
    def __init__(self, guild_id, settings):
        pass  # Dummy cog object just for holding settings


def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a


def coprime(a, b):
    return gcd(a, b) == 1


def mod_inverse(a, m):
    a = a % m;
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return 1


def encode(number, alphabet, max_length):
    """
    Turns a number into that number represented by teh character in
    the 'cypher' settings for the guild we're encoding on.
    """

    n_original = number

    alph = ""
    alph_zero = alphabet[0]
    if number == 0:
        alph = alph_zero
    while number != 0:
        digit = number % len(alphabet)
        alph = alphabet[digit] + alph
        number = (number - digit) // len(alphabet)
    while len(alph) < max_length:
        alph = alph_zero + alph

    return alph


def decode(alph, alphabet):
    """
    Turns a string representation from a number, such as the one
    retuned by encode above, back into the original number.
    """

    n_symbols = len(alphabet)
    n = 0
    for digit in alph:
        v = alphabet.find(digit)
        n = n_symbols * n + v

    return n


def scramble(data, guild):
    """This is not supposed to be secure - it's just to obfuscate the fact it's an index in a list"""

    identifier = solon.get_identifier("cypher", guild.id)
    alphabet = solon.get_setting_value(identifier, "alphabet")
    max_length = solon.get_setting_value(identifier, "max_length")
    cypher = solon.get_setting_value(identifier, "cypher")
    offset = solon.get_setting_value(identifier, "offset")

    n_possibs = len(alphabet) ** max_length

    s = (cypher * data + offset) % n_possibs
    alph = encode(s, alphabet, max_length)

    return alph


def unscramble(alph, guild):
    """This is not supposed to be secure - it's just to obfuscate the fact it's an index in a list"""

    identifier = solon.get_identifier("cypher", guild.id)
    alphabet = solon.get_setting_value(identifier, "alphabet")
    max_length = solon.get_setting_value(identifier, "max_length")
    cypher = solon.get_setting_value(identifier, "cypher")
    offset = solon.get_setting_value(identifier, "offset")

    n_possibs = len(alphabet) ** max_length

    s = decode(alph, alphabet)
    decypher = mod_inverse(cypher, n_possibs)
    data = (decypher * (s - offset) + n_possibs) % n_possibs

    return data
