/// 客户端默认配置。不含任何服务器密钥。
class AppConfig {
  static const defaultOrigin = 'http://8.148.186.220';
  static const apiPrefix = '/api/v1';
  static const healthPath = '/health';
  static const appName = '校园助手';
  static const appFullName = '校园办事与入学助手';
  static const connectTimeout = Duration(seconds: 12);
  static const receiveTimeout = Duration(seconds: 30);

  /// 把用户输入规范成源站（去掉末尾斜线与误填的 /api/v1）。
  static String normalizeOrigin(String input) {
    var u = input.trim();
    if (u.isEmpty) return defaultOrigin;
    if (!u.startsWith('http://') && !u.startsWith('https://')) {
      u = 'http://$u';
    }
    while (u.endsWith('/')) {
      u = u.substring(0, u.length - 1);
    }
    const suffixes = ['/api/v1', '/api'];
    for (final s in suffixes) {
      if (u.toLowerCase().endsWith(s)) {
        u = u.substring(0, u.length - s.length);
        break;
      }
    }
    return u;
  }

  static String apiRoot(String origin) => '${normalizeOrigin(origin)}$apiPrefix';

  static String healthUrl(String origin) =>
      '${normalizeOrigin(origin)}$healthPath';
}
