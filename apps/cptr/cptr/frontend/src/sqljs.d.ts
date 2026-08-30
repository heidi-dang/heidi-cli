declare module 'sql.js' {
	interface SqlJsConfig {
		locateFile?: (file: string) => string;
	}

	interface SqlJsStatic {
		Database: new (data?: Uint8Array) => any;
	}

	export default function initSqlJs(config?: SqlJsConfig): Promise<SqlJsStatic>;
}
