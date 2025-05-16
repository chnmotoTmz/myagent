"""
アプリケーション固有の例外クラスを定義するモジュール
"""

class AmebaAutomationError(Exception):
    """アプリケーション全体の基底例外クラス"""
    pass

# ブラウザ関連の例外
class BrowserError(AmebaAutomationError):
    """ブラウザ操作に関する基底例外クラス"""
    pass

class BrowserInitializationError(BrowserError):
    """ブラウザの初期化に失敗した場合の例外"""
    pass

class LoginError(BrowserError):
    """ログインに失敗した場合の例外"""
    pass

# データベース関連の例外
class DatabaseError(AmebaAutomationError):
    """データベース操作に関する基底例外クラス"""
    pass

class PostNotFoundError(DatabaseError):
    """投稿が見つからない場合の例外"""
    pass

class DatabaseConnectionError(DatabaseError):
    """データベース接続に失敗した場合の例外"""
    pass

# GUI関連の例外
class GUIError(AmebaAutomationError):
    """GUI操作に関する基底例外クラス"""
    pass

class WidgetError(GUIError):
    """ウィジェット操作に失敗した場合の例外"""
    pass

# URL関連の例外
class URLError(AmebaAutomationError):
    """URL操作に関する基底例外クラス"""
    pass

class URLTransformError(URLError):
    """URL変換に失敗した場合の例外"""
    pass 