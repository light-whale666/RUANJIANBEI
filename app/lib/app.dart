import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'config/app_config.dart';
import 'screens/login_screen.dart';
import 'screens/shell_screen.dart';
import 'state/session.dart';
import 'theme/app_theme.dart';

class CampusApp extends StatefulWidget {
  const CampusApp({super.key});

  @override
  State<CampusApp> createState() => _CampusAppState();
}

class _CampusAppState extends State<CampusApp> {
  final Session _session = Session();

  @override
  void initState() {
    super.initState();
    _session.bootstrap();
  }

  @override
  void dispose() {
    _session.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: _session,
      child: MaterialApp(
        title: AppConfig.appName,
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        locale: const Locale('zh'),
        supportedLocales: const [Locale('zh'), Locale('en')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: Consumer<Session>(
          builder: (context, session, _) {
            if (!session.ready) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }
            return session.loggedIn ? const ShellScreen() : const LoginScreen();
          },
        ),
      ),
    );
  }
}
