import 'dart:convert';

import 'package:http/http.dart' as http;

/// 查账问答：把账目数据 + 用户问题发给 DeepSeek，返回一段口语化回答。
///
/// 与 [LlmEntryParser] 共用 DeepSeek OpenAI 兼容接口，但这里要的是自由文本回答
/// （非 JSON），用于「喵助手」的查账 / 消费分析。
class LlmQuery {
  LlmQuery._();

  static const _endpoint = 'https://api.deepseek.com/chat/completions';
  static const _model = 'deepseek-chat';
  static const _timeoutSeconds = 30;

  /// 根据 [transactionsText]（账目上下文）回答 [question]。
  /// 失败抛 [LlmQueryException]。
  static Future<String> ask({
    required String question,
    required String apiKey,
    required String transactionsText,
  }) async {
    final systemPrompt =
        '''你是「喵助手」，一只蓝白英短猫记账助理。根据下面的账目数据回答用户的问题。
要求：口语化、简短亲切、可以带一点猫咪语气（偶尔用「喵」）；涉及金额要给具体数字（单位元）；
算不出或数据里没有就如实说不知道，绝不编造。不要用 Markdown 表格，普通文字即可。

$transactionsText''';

    final body = jsonEncode({
      'model': _model,
      'messages': [
        {'role': 'system', 'content': systemPrompt},
        {'role': 'user', 'content': question},
      ],
      'stream': false,
    });

    late http.Response resp;
    try {
      resp = await http
          .post(
            Uri.parse(_endpoint),
            headers: {
              'Authorization': 'Bearer $apiKey',
              'Content-Type': 'application/json',
            },
            body: body,
          )
          .timeout(const Duration(seconds: _timeoutSeconds));
    } catch (e) {
      throw LlmQueryException('网络请求失败：$e');
    }

    if (resp.statusCode != 200) {
      throw LlmQueryException('DeepSeek 返回错误 ${resp.statusCode}');
    }

    try {
      final outer = jsonDecode(resp.body) as Map<String, dynamic>;
      final content =
          (outer['choices'] as List).first['message']['content'] as String;
      final text = content.trim();
      if (text.isEmpty) throw const LlmQueryException('空回答');
      return text;
    } catch (e) {
      throw LlmQueryException('响应解析失败：$e');
    }
  }

  /// 轻量「测试连接」：用最小请求验证 [apiKey] 是否可用。
  /// 成功正常返回；失败抛 [LlmQueryException]（带可读中文原因）。
  /// 不复用 [ask]，避免无谓地拼接账目上下文。
  static Future<void> testConnection(String apiKey) async {
    final key = apiKey.trim();
    if (key.isEmpty) {
      throw const LlmQueryException('还没填 API Key');
    }

    final body = jsonEncode({
      'model': _model,
      'messages': [
        {'role': 'user', 'content': 'ping'},
      ],
      'max_tokens': 1,
      'stream': false,
    });

    late http.Response resp;
    try {
      resp = await http
          .post(
            Uri.parse(_endpoint),
            headers: {
              'Authorization': 'Bearer $key',
              'Content-Type': 'application/json',
            },
            body: body,
          )
          .timeout(const Duration(seconds: 15));
    } catch (e) {
      throw LlmQueryException('网络请求失败：$e');
    }

    switch (resp.statusCode) {
      case 200:
        return; // 连接成功
      case 401:
        throw const LlmQueryException('API Key 无效（401 未授权）');
      case 402:
        throw const LlmQueryException('账户余额不足（402）');
      case 429:
        throw const LlmQueryException('请求过于频繁，稍后再试（429）');
      default:
        throw LlmQueryException('DeepSeek 返回错误 ${resp.statusCode}');
    }
  }
}

class LlmQueryException implements Exception {
  final String message;
  const LlmQueryException(this.message);
  @override
  String toString() => 'LlmQueryException: $message';
}
