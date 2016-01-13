class CardConvertError(Exception):
    def __init__(self, value, return_code, stdout, stderr):
        self.value = value
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        info = '%s\nReturn Code:%s\nSTDOUT:%s\nSTDERR:%s\n' % (self.value, self.return_code, self.stdout, self.stderr)
        return repr(info)


class MakeMediumCopyError(CardConvertError):
    pass


class MakeSmallCopyError(CardConvertError):
    pass


class MakeJpgCopyError(CardConvertError):
    pass


class MakeSmallIconError(CardConvertError):
    pass


class MakeMediumIconError(CardConvertError):
    pass


class MakeLargeIconError(CardConvertError):
    pass


class MakeAnimatedPNGError(CardConvertError):
    pass


class MakeAnimatedGIFError(CardConvertError):
    pass


class MakeMP4Error(CardConvertError):
    pass


class MakeWEBMError(CardConvertError):
    pass


class MakeCompositeError(CardConvertError):
    pass