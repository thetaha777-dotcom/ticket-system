import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../theme.dart';
import 'attendee/catalogue_screen.dart';
import 'attendee/tickets_screen.dart';
import 'events_screen.dart';
import 'login_screen.dart';

enum HomeTab { events, tickets, checkIn }

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  HomeTab _tab = HomeTab.events;
  String? _userId;

  bool _assignedAsStaff = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final user = context.session.user;
    if (user?.id == _userId) return; // nobody signed in or out
    _userId = user?.id;
    _assignedAsStaff = false;
    if (user?.role == 'event_admin') _tab = HomeTab.checkIn; // staff open straight on the door tools
    if (user != null && !user.worksAtEvents) {
      context.session.api.events().then((events) {
        if (mounted && _userId == user.id && events.isNotEmpty) setState(() => _assignedAsStaff = true);
      }, onError: (Object _) {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.session.user;
    final tabs = [HomeTab.events, HomeTab.tickets, if (user != null && (user.worksAtEvents || _assignedAsStaff)) HomeTab.checkIn];
    final tab = tabs.contains(_tab) ? _tab : HomeTab.events;
    return Scaffold(
      body: KeyedSubtree(
        key: ValueKey('$tab-$_userId'), // each tab loads fresh data when it is opened
        child: switch (tab) {
          HomeTab.events => const CatalogueScreen(),
          HomeTab.tickets => user == null ? const _SignInPrompt() : const TicketsScreen(),
          HomeTab.checkIn => const EventsScreen(),
        },
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tabs.indexOf(tab),
        onDestinationSelected: (index) => setState(() => _tab = tabs[index]),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.explore_outlined), label: context.t('tabEvents')),
          NavigationDestination(icon: const Icon(Icons.confirmation_number_outlined), label: context.t('navTickets')),
          if (tabs.contains(HomeTab.checkIn)) NavigationDestination(icon: const Icon(Icons.qr_code_scanner), label: context.t('tabCheckIn')),
        ],
      ),
    );
  }
}

class _SignInPrompt extends StatelessWidget {
  const _SignInPrompt();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.t('tabTickets'))),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(context.t('signInToBuy'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 17, color: AppColors.ink)),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute<bool>(builder: (_) => const LoginScreen())),
                child: Text(context.t('signIn')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
