from pysim_sdk.utils.ip_address import ip2str


class RoutingTable:
    def __init__(self, default_gateway):
        self.initial_gateway = default_gateway
        self.default_gateway = Hop(0, 0, default_gateway, True)
        self.first = self.default_gateway
        self.routes = [self.default_gateway]

    @staticmethod
    def from_json(table):
        routes = []
        for ip, mask, interface in table:
            routes.append(Hop(ip, mask.bit_count(), interface, False))

        table = RoutingTable(routes[-1].interface)
        table.default_gateway = routes[-1]
        table.default_gateway.static = True
        table.first = routes[0]
        table.routes = routes
        return table

    def json(self):
        return [[r.ip, r.mask, r.interface] for r in self.routes]

    def reset(self):
        self.default_gateway = Hop(0, 0, self.initial_gateway, True)
        self.first = self.default_gateway
        self.routes = [self.default_gateway]

    def add_route_with_mask(self, ip, mask, interface, static=False):
        self.add_route(ip, mask.bit_count(), interface, static)

    def add_route(self, ip, prefix_len, interface, static=False):
        for i, route in enumerate(self.routes):
            if route.prefix_len <= prefix_len:
                break

        self.routes.insert(i, Hop(ip, prefix_len, interface, static))

    def switch_default_gateway(self, interface):
        self.default_gateway.interface = interface

    def route(self, ip):
        for route in self.routes:
            if route.matches(ip):
                return route
        return None

    def remove_route(self, ip, prefix_len):
        self.routes = [
            route
            for route in self.routes
            if route.ip != ip or route.prefix_len != prefix_len
        ]

    def remove_routes_for_interface(self, interface):
        """
        Removes all routes for a given interface, with exception of routes marked
        as `assets`.
        """
        lost_routes = [
            route
            for route in self.routes
            if route.interface == interface and not route.static
        ]

        self.routes = [route for route in self.routes if route not in lost_routes]
        return lost_routes

    def __str__(self):
        result = ""
        for route in self.routes:
            result += "  " + str(route) + "\n"
        return result.rstrip("\n")

    def status(self):
        return [str(route) for route in self.routes]


class Hop:
    def __init__(self, ip, prefix_len, interface, static=False):
        self.static = static
        self.prefix_len = prefix_len
        self.mask = ((1 << prefix_len) - 1) << (32 - prefix_len)
        self.ip = ip & self.mask
        self.interface = interface
        self.next = None

    def matches(self, ip: int):
        return (ip & self.mask) == self.ip

    def __str__(self):
        static_mark = ""
        if self.static:
            static_mark = "[STATIC] "
        return static_mark + ip2str(self.ip) + f"/{self.prefix_len} -> {self.interface}"
